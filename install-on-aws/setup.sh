#!/bin/bash

# This creates $vm_count + 1 VMs
bash create_vms.sh
sleep 10
bash mount_volume.sh