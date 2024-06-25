#!/bin/bash

# Submit Nomad Job Script

ssh_command="$1"
hcl_filename="$2"
acl_token="$3"
shift 3
additional_args=("$@")

# Function to determine OS type
get_os_type() {
    case "$(uname -s)" in
        Darwin)
            echo "macOS"
            ;;
        Linux)
            echo "Linux"
            ;;
        *)
            echo "Unknown"
            ;;
    esac
}

# Function to use sed with correct syntax based on OS
sed_in_place() {
    local os_type=$(get_os_type)
    local sed_cmd=""

    if [ "$os_type" = "macOS" ]; then
        # macOS requires an empty string as an argument to -i
        sed_cmd="sed -i ''"
    else
        sed_cmd="sed -i"
    fi

    # Run the sed command
    $sed_cmd "$@"
}

# Function to replace placeholders in HCL file
replace_placeholders() {
    local filepath=$1
    local output_file=$(mktemp)  # Create a temporary file

    # Make a copy of the file to the temp file
    cp "$filepath" "$output_file"

    # Replace each placeholder with the value of the corresponding environment variable
    for var in "${additional_args[@]}"; do
        key=$(echo "$var" | cut -d '=' -f 1)
        value=$(echo "$var" | cut -d '=' -f 2)
        sed_in_place "s|{{ $key }}|$value|g" "$output_file"
    done

    echo "$output_file"
}

# Function to submit job to Nomad
submit_nomad_job() {
    local ssh_command=$1
    local filepath=$2
    local acl_token=$3
    local temp_hcl_file headers json_payload_url submit_url json_payload response

    # Replace placeholders
    temp_hcl_file=$(replace_placeholders "$filepath")

    hcl_content=$(<"$temp_hcl_file")

    # Construct HCL payload
    hcl_payload=$(jq -n --arg hcl "$hcl_content" '{JobHCL: $hcl, Canonicalize: true}')

    $ssh_command <<EOF
        content_header="Content-Type: application/json"
        token_header="X-Nomad-Token: $acl_token"
        hcl_to_json_url="http://localhost:4646/v1/jobs/parse"
        submit_job_url="http://localhost:4646/v1/jobs"

        hcl_payload='$hcl_payload'

        # Convert HCL to JSON using the Nomad API
        json_payload=\$(curl -s -X POST -H "\$content_header" -H "\$token_header" -d "\$hcl_payload" "\$hcl_to_json_url")
        echo \$json_payload

        # Submit JSON to Nomad
        response=\$(curl -s -X POST -H "\$content_header" -H "\$token_header" -d "{\"Job\":\$json_payload}" "\$submit_job_url")
        echo \$response
EOF

    # Cleanup temporary file
    rm "$temp_hcl_file"
}

# Main execution
submit_nomad_job "$ssh_command" "$hcl_filename" "$acl_token"
