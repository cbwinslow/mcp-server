ANSIBLE?=ansible-playbook -i ansible/inventory.ini

.PHONY: ansible-install
ansible-install:
	ansible-galaxy collection install -r ansible/requirements.yml

.PHONY: deploy
deploy:
	$(ANSIBLE) ansible/site.yml

.PHONY: check
check:
	$(ANSIBLE) ansible/checks.yml

.PHONY: migrate
migrate:
	$(ANSIBLE) ansible/migrate.yml

.PHONY: tf-init tf-apply
tf-init:
	cd infra/terraform/cloudflare && terraform init

tf-apply:
	cd infra/terraform/cloudflare && terraform apply

.PHONY: tfvars-render
tfvars-render:
	$(ANSIBLE) ansible/tfvars.yml

.PHONY: pulumi-preview pulumi-up
pulumi-preview:
	cd infra/pulumi/cloudflare && pulumi preview

pulumi-up:
	cd infra/pulumi/cloudflare && pulumi up
