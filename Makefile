# Simple Makefile for Ansible deployments

INVENTORY ?= inventory/production/hosts

help:
	@echo "Available commands:"
	@echo "  make install       - Install Python dependencies (uv sync)"
	@echo "  make create-vm VM_NAME=ar-io-node-X - Create new VM"
	@echo "  make delete-vm     - Delete VM (interactive selection)"
	@echo "  make list-vms      - List all VMs"
	@echo "  make deploy-ar-io [HOST=hostname] - Deploy AR.IO nodes"
	@echo "  make cleanup-ar-io [HOST=hostname] - Remove AR.IO installation"
	@echo "  make test          - Test connectivity"

setup:
	./setup.sh

install:
	uv sync

test:
	ansible -i $(INVENTORY) all -m ping

deploy-ar-io:
	@if [ -n "$(HOST)" ]; then \
		ansible-playbook -i $(INVENTORY) --limit $(HOST) playbooks/deploy-ar-io.yml; \
	else \
		ansible-playbook -i $(INVENTORY) playbooks/deploy-ar-io.yml; \
	fi

cleanup-ar-io:
	@if [ -n "$(HOST)" ]; then \
		ansible-playbook -i $(INVENTORY) --limit $(HOST) playbooks/cleanup-ar-io.yml; \
	else \
		ansible-playbook -i $(INVENTORY) playbooks/cleanup-ar-io.yml; \
	fi

create-vm:
	@if [ -z "$(VM_NAME)" ]; then echo "Usage: make create-vm VM_NAME=ar-io-node-X"; exit 1; fi
	python scripts/fluence_vm.py create $(VM_NAME)

delete-vm:
	python scripts/fluence_vm.py delete

list-vms:
	python scripts/fluence_vm.py list

.PHONY: help setup install test deploy-ar-io cleanup-ar-io create-vm delete-vm list-vms