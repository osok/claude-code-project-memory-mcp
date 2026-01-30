# Kubernetes Testing Conventions

## Test Structure

```
k8s/
├── base/
├── overlays/
└── tests/
    ├── unit/
    │   └── manifests_test.yaml    # kubeconform/kubeval
    ├── integration/
    │   └── deployment_test.go      # kind + Go
    ├── e2e/
    │   └── smoke_test.sh
    └── policies/
        └── deployment_policy.rego  # OPA/Gatekeeper
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{resource}_test.{ext}` | `deployment_test.go` |
| Policy | `{resource}_policy.rego` | `deployment_policy.rego` |
| Fixture | `{name}_fixture.yaml` | `pod_fixture.yaml` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Schema validation | kubeconform | Fast YAML validation |
| Policy testing | OPA/Conftest | Rego policies |
| Integration | kind + kubectl | Local cluster |
| E2E | Terratest / Go | Full deployment |
| Security | Trivy, Kubesec | Security scanning |

## Test Commands

| Action | Command |
|--------|---------|
| Validate | `kubeconform -strict base/` |
| Policy test | `conftest test base/ -p tests/policies/` |
| Integration | `go test -v ./tests/integration/...` |
| E2E | `./tests/e2e/smoke_test.sh` |
| Security | `trivy config base/` |

## Schema Validation (kubeconform)

```bash
#!/bin/bash
# tests/validate.sh

# Validate all manifests
kubeconform \
  -strict \
  -summary \
  -output json \
  -kubernetes-version 1.28.0 \
  -ignore-missing-schemas \
  base/

# Validate kustomize output
kustomize build overlays/prod | kubeconform -strict -summary
```

## Policy Testing (Conftest/OPA)

```rego
# tests/policies/deployment_policy.rego
package main

deny[msg] {
  input.kind == "Deployment"
  not input.spec.template.spec.securityContext.runAsNonRoot
  msg := "Deployments must set runAsNonRoot: true"
}

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.resources.limits.memory
  msg := sprintf("Container %s must set memory limits", [container.name])
}

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.resources.limits.cpu
  msg := sprintf("Container %s must set CPU limits", [container.name])
}

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.livenessProbe
  msg := sprintf("Container %s must have a liveness probe", [container.name])
}

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.readinessProbe
  msg := sprintf("Container %s must have a readiness probe", [container.name])
}

warn[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  container.image
  not contains(container.image, ":")
  msg := sprintf("Container %s should use explicit image tag", [container.name])
}
```

## Integration Tests (Go + kind)

```go
// tests/integration/deployment_test.go
package integration

import (
    "context"
    "testing"
    "time"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
    appsv1 "k8s.io/api/apps/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/client-go/kubernetes"
    "sigs.k8s.io/e2e-framework/pkg/envconf"
    "sigs.k8s.io/e2e-framework/pkg/features"
)

func TestDeploymentRollout(t *testing.T) {
    feature := features.New("deployment rollout").
        Setup(func(ctx context.Context, t *testing.T, cfg *envconf.Config) context.Context {
            // Apply manifests
            client := cfg.Client()
            err := applyManifests(ctx, client, "../../overlays/test")
            require.NoError(t, err)
            return ctx
        }).
        Assess("deployment becomes ready", func(ctx context.Context, t *testing.T, cfg *envconf.Config) context.Context {
            client := cfg.Client()

            // Wait for deployment to be ready
            err := waitForDeployment(ctx, client, "my-app", "user-service", 60*time.Second)
            require.NoError(t, err)

            // Verify replicas
            deployment, err := client.AppsV1().Deployments("my-app").
                Get(ctx, "user-service", metav1.GetOptions{})
            require.NoError(t, err)

            assert.Equal(t, int32(2), *deployment.Spec.Replicas)
            assert.Equal(t, int32(2), deployment.Status.ReadyReplicas)

            return ctx
        }).
        Assess("service is accessible", func(ctx context.Context, t *testing.T, cfg *envconf.Config) context.Context {
            // Port forward and test endpoint
            err := testServiceEndpoint(ctx, "my-app", "user-service", "/health")
            require.NoError(t, err)
            return ctx
        }).
        Teardown(func(ctx context.Context, t *testing.T, cfg *envconf.Config) context.Context {
            // Cleanup
            return ctx
        }).
        Feature()

    testenv.Test(t, feature)
}
```

## E2E Smoke Test

```bash
#!/bin/bash
# tests/e2e/smoke_test.sh
set -e

NAMESPACE="my-app-e2e"
TIMEOUT="120s"

echo "Creating test namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "Applying manifests..."
kustomize build overlays/test | kubectl apply -n $NAMESPACE -f -

echo "Waiting for deployment..."
kubectl rollout status deployment/user-service -n $NAMESPACE --timeout=$TIMEOUT

echo "Checking pod health..."
POD=$(kubectl get pod -n $NAMESPACE -l app.kubernetes.io/name=user-service -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n $NAMESPACE $POD -- wget -q -O- http://localhost:8080/health/ready

echo "Testing service connectivity..."
kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -n $NAMESPACE -- \
    curl -s http://user-service/health

echo "Cleaning up..."
kubectl delete namespace $NAMESPACE

echo "All tests passed!"
```

## Security Scanning

```yaml
# .trivyignore
# Ignore specific CVEs if needed
CVE-2023-XXXXX
```

```bash
# Scan for misconfigurations
trivy config base/

# Scan container images
trivy image myregistry/user-service:latest

# Scan Kubernetes cluster
trivy k8s --report summary cluster
```

## CI Pipeline Example

```yaml
# .github/workflows/k8s-test.yaml
name: Kubernetes Tests

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate manifests
        run: |
          kubeconform -strict -summary base/

      - name: Policy check
        run: |
          conftest test base/ -p tests/policies/

      - name: Security scan
        run: |
          trivy config base/

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create kind cluster
        uses: helm/kind-action@v1

      - name: Run integration tests
        run: |
          go test -v ./tests/integration/...
```

## Coverage Target

- 100% schema validation
- Policy tests for security requirements
- Integration tests for critical deployments
- E2E smoke tests before production
