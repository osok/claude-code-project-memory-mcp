# Terraform Testing Conventions

## Test Structure

```
infrastructure/
├── modules/
│   └── vpc/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── tests/
│           ├── vpc_test.go        # Terratest
│           └── vpc.tftest.hcl     # Native test
├── tests/
│   ├── integration/
│   │   └── full_stack_test.go
│   └── fixtures/
│       └── test.tfvars
└── Makefile
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file (native) | `{module}.tftest.hcl` | `vpc.tftest.hcl` |
| Test file (Terratest) | `{module}_test.go` | `vpc_test.go` |
| Test function | `Test{Module}{Scenario}` | `TestVpcCreation` |
| Fixture | `{name}.tfvars` | `test.tfvars` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Native testing | terraform test | Built-in (1.6+) |
| Integration | Terratest | Go-based |
| Linting | tflint | Static analysis |
| Security | Checkov, tfsec | Security scanning |
| Cost | Infracost | Cost estimation |

## Test Commands

| Action | Command |
|--------|---------|
| Native test | `terraform test` |
| Terratest | `go test -v ./tests/...` |
| Lint | `tflint --recursive` |
| Security | `checkov -d .` |
| Validate | `terraform validate` |

## Native Tests (terraform test)

```hcl
# modules/vpc/tests/vpc.tftest.hcl
variables {
  name               = "test"
  vpc_cidr           = "10.0.0.0/16"
  public_subnets     = ["10.0.1.0/24", "10.0.2.0/24"]
  availability_zones = ["us-east-1a", "us-east-1b"]
  tags               = { Environment = "test" }
}

run "creates_vpc_with_correct_cidr" {
  command = plan

  assert {
    condition     = aws_vpc.main.cidr_block == "10.0.0.0/16"
    error_message = "VPC CIDR block is incorrect"
  }
}

run "creates_correct_number_of_subnets" {
  command = plan

  assert {
    condition     = length(aws_subnet.public) == 2
    error_message = "Expected 2 public subnets"
  }
}

run "applies_tags_correctly" {
  command = plan

  assert {
    condition     = aws_vpc.main.tags["Environment"] == "test"
    error_message = "Environment tag not applied"
  }
}

run "outputs_vpc_id" {
  command = plan

  assert {
    condition     = output.vpc_id != null
    error_message = "VPC ID output is null"
  }
}
```

## Terratest (Go)

```go
// tests/vpc_test.go
package test

import (
    "testing"

    "github.com/gruntwork-io/terratest/modules/aws"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestVpcModule(t *testing.T) {
    t.Parallel()

    awsRegion := "us-east-1"

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/vpc",
        Vars: map[string]interface{}{
            "name":               "terratest",
            "vpc_cidr":           "10.99.0.0/16",
            "public_subnets":     []string{"10.99.1.0/24", "10.99.2.0/24"},
            "availability_zones": []string{"us-east-1a", "us-east-1b"},
            "tags": map[string]string{
                "Environment": "test",
            },
        },
        EnvVars: map[string]string{
            "AWS_DEFAULT_REGION": awsRegion,
        },
    })

    defer terraform.Destroy(t, terraformOptions)

    terraform.InitAndApply(t, terraformOptions)

    // Get outputs
    vpcID := terraform.Output(t, terraformOptions, "vpc_id")
    subnetIDs := terraform.OutputList(t, terraformOptions, "public_subnet_ids")

    // Verify VPC exists
    vpc := aws.GetVpcById(t, vpcID, awsRegion)
    assert.Equal(t, "10.99.0.0/16", *vpc.CidrBlock)

    // Verify subnets
    assert.Len(t, subnetIDs, 2)

    // Verify tags
    assert.Equal(t, "test", vpc.Tags["Environment"])
}

func TestVpcModuleValidation(t *testing.T) {
    t.Parallel()

    terraformOptions := &terraform.Options{
        TerraformDir: "../modules/vpc",
        Vars: map[string]interface{}{
            "name":               "",  // Invalid: empty name
            "vpc_cidr":           "10.0.0.0/16",
            "public_subnets":     []string{},
            "availability_zones": []string{},
        },
    }

    _, err := terraform.InitAndPlanE(t, terraformOptions)
    assert.Error(t, err, "Expected validation error for empty name")
}
```

## Integration Tests

```go
// tests/integration/full_stack_test.go
package integration

import (
    "testing"
    "time"

    "github.com/gruntwork-io/terratest/modules/http-helper"
    "github.com/gruntwork-io/terratest/modules/terraform"
)

func TestFullStackDeployment(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../../environments/test",
        VarFiles:     []string{"../fixtures/test.tfvars"},
    })

    defer terraform.Destroy(t, terraformOptions)

    terraform.InitAndApply(t, terraformOptions)

    // Get the ALB URL
    albURL := terraform.Output(t, terraformOptions, "alb_dns_name")

    // Verify the application is accessible
    http_helper.HttpGetWithRetry(
        t,
        "http://"+albURL+"/health",
        nil,
        200,
        "OK",
        30,
        10*time.Second,
    )
}
```

## Linting Configuration

```hcl
# .tflint.hcl
plugin "aws" {
  enabled = true
  version = "0.29.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "aws_resource_missing_tags" {
  enabled = true
  tags    = ["Environment", "Project"]
}
```

## Security Scanning

```yaml
# .checkov.yaml
compact: true
framework:
  - terraform
skip-check:
  - CKV_AWS_18  # S3 access logging
  - CKV_AWS_21  # S3 versioning
soft-fail-on:
  - CKV_AWS_*
```

## Makefile

```makefile
.PHONY: init plan apply test lint

init:
	terraform init

plan:
	terraform plan -var-file=terraform.tfvars

apply:
	terraform apply -var-file=terraform.tfvars

test:
	terraform test

test-integration:
	cd tests && go test -v -timeout 30m ./...

lint:
	terraform fmt -check -recursive
	terraform validate
	tflint --recursive
	checkov -d .
```

## Coverage Target

- Test all modules with native tests
- Integration tests for critical infrastructure
- Security scan on every PR
- Cost estimation on changes
