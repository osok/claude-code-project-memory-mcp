# Kubernetes Conventions

## Project Structure

```
k8s/
├── base/                    # Base configurations
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── kustomization.yaml
├── overlays/                # Environment-specific
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   ├── deployment-patch.yaml
│   │   └── configmap.yaml
│   ├── staging/
│   └── prod/
├── components/              # Reusable components
│   ├── monitoring/
│   └── logging/
└── charts/                  # Helm charts
    └── myapp/
        ├── Chart.yaml
        ├── values.yaml
        └── templates/
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Namespace | lowercase, hyphenated | `my-app-prod` |
| Deployment | lowercase, hyphenated | `user-service` |
| Service | same as deployment | `user-service` |
| ConfigMap | lowercase + config | `user-service-config` |
| Secret | lowercase + secret | `user-service-secret` |
| Labels | lowercase | `app.kubernetes.io/name` |

## Standard Labels

```yaml
metadata:
  labels:
    app.kubernetes.io/name: user-service
    app.kubernetes.io/instance: user-service-prod
    app.kubernetes.io/version: "1.2.3"
    app.kubernetes.io/component: api
    app.kubernetes.io/part-of: my-app
    app.kubernetes.io/managed-by: helm
```

## Commands

| Action | Command |
|--------|---------|
| Apply | `kubectl apply -f manifest.yaml` |
| Apply dir | `kubectl apply -k overlays/dev/` |
| Get pods | `kubectl get pods -n namespace` |
| Describe | `kubectl describe pod/name` |
| Logs | `kubectl logs pod/name -f` |
| Exec | `kubectl exec -it pod/name -- /bin/sh` |
| Port forward | `kubectl port-forward svc/name 8080:80` |
| Delete | `kubectl delete -f manifest.yaml` |

## Deployment Template

```yaml
# base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
  labels:
    app.kubernetes.io/name: user-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: user-service
  template:
    metadata:
      labels:
        app.kubernetes.io/name: user-service
    spec:
      serviceAccountName: user-service
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: user-service
          image: myregistry/user-service:latest
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          envFrom:
            - configMapRef:
                name: user-service-config
            - secretRef:
                name: user-service-secret
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health/live
              port: http
            initialDelaySeconds: 15
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
```

## Service Template

```yaml
# base/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
  labels:
    app.kubernetes.io/name: user-service
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: http
      protocol: TCP
      name: http
  selector:
    app.kubernetes.io/name: user-service
```

## ConfigMap Template

```yaml
# base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-service-config
data:
  LOG_LEVEL: "info"
  DATABASE_HOST: "postgres.database.svc.cluster.local"
  CACHE_HOST: "redis.cache.svc.cluster.local"
```

## Kustomization

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: my-app

commonLabels:
  app.kubernetes.io/part-of: my-app

resources:
  - namespace.yaml
  - deployment.yaml
  - service.yaml
  - configmap.yaml

# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: my-app-prod

resources:
  - ../../base

patches:
  - path: deployment-patch.yaml

configMapGenerator:
  - name: user-service-config
    behavior: merge
    literals:
      - LOG_LEVEL=warn

replicas:
  - name: user-service
    count: 5
```

## Code Style

- Use Kustomize for configuration management
- Always set resource requests and limits
- Use health probes (liveness + readiness)
- Run containers as non-root
- Use read-only root filesystem
- Drop all capabilities
- Use namespaces for isolation
- Label everything consistently
- Use secrets for sensitive data
