# Simple Makefile for Ansible deployments

INVENTORY ?= inventory/production/hosts

help:
	@echo "Available commands:"
	@echo "  make install       - Install Python dependencies (uv sync)"
	@echo "  make deploy-ar-io  - Deploy AR.IO nodes"
	@echo "  make cleanup-ar-io - Remove AR.IO installation"
	@echo "  make test          - Test connectivity"

setup:
	./setup.sh

install:
	uv sync

test:
	ansible -i $(INVENTORY) all -m ping

deploy-ar-io:
	ansible-playbook -i $(INVENTORY) playbooks/deploy-ar-io.yml

cleanup-ar-io:
	ansible-playbook -i $(INVENTORY) playbooks/cleanup-ar-io.yml

.PHONY: help setup install test deploy-ar-io cleanup-ar-io