from argparse import ArgumentParser
import requests
from jinja2 import Template


def get_hcl_payload(filepath, is_jinja, **kwargs):
    with open(filepath, 'r') as file:
        content = file.read()

    if is_jinja:
        template = Template(content)
        hcl_content = template.render(**kwargs)
    else:
        hcl_content = content

    payload = {
        'JobHCL': hcl_content,
        'Canonicalize': True
    }

    return payload

def submit_nomad_job(filepath, nomad_endpoint, **kwargs):
    """ 
    This function submits an generated HCL job file from a jinja file to nomad 
    """

    json_payload_url = f"{nomad_endpoint}v1/jobs/parse"
    submit_url = f"{nomad_endpoint}v1/jobs"
    headers = {
        'Content-Type': 'application/json'
    }

    filepath_ext = filepath.split(".")[-1]
    is_jinja = filepath_ext == "j2"
    hcl_payload = get_hcl_payload(filepath, is_jinja=is_jinja, **kwargs)

    # Before submitting a job to nomad, we must convert the HCL file to JSON
    json_payload_response = requests.post(json_payload_url, headers=headers, json=hcl_payload)
    json_payload = json_payload_response.json()
    print(json_payload_response.text)

    # Submit the JSON job spec to Nomad
    response = requests.post(submit_url, headers=headers, json={"Job": json_payload})
    print(response.text)

    return response

if __name__ == "__main__":
    parser = ArgumentParser("Submit Nomad Job")
    parser.add_argument("--nomad-ip", type=str)
    parser.add_argument("--hcl-template-filename", type=str)
    parser.add_argument('args', nargs='*', type=lambda kv: kv.split("=", 1), help='Additional key-value pair arguments in the format key=value')

    args = parser.parse_args()

    kwargs = {k: v for k, v in args.args}
    submit_nomad_job(args.hcl_template_filename, f"http://{args.nomad_ip}:4646/", **kwargs)