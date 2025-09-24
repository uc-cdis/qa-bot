#!/bin/bash

# Function to scale all deployments to zero and suspend all cronjobs in a namespace
# Add this to your ~/.bashrc or ~/.zshrc to use as: scaleup-namespace <namespace>

scaleup-namespace() {
    # Check if namespace argument is provided
    if [ $# -eq 0 ]; then
        echo "Error: No namespace provided"
        echo "Usage: scaleup-namespace <namespace>"
        return 1
    fi

    local NAMESPACE=$1

    # Verify namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        echo "Error: Namespace '$NAMESPACE' does not exist"
        return 1
    fi

    # Confirmation prompt
    echo "WARNING: This will scale all deployments to 1 replicas and restart all cronjobs in namespace: '$NAMESPACE'"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRMATION

    if [ "$CONFIRMATION" != "yes" ]; then
        echo "Operation cancelled."
        return 0
    fi

    echo ""
    echo "Bringing up resources in namespace: $NAMESPACE"
    echo "=========================================="

    # Scale all deployments to zero
    echo "Scaling deployments to 1 replicas..."
    local DEPLOYMENTS=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

    if [ -n "$DEPLOYMENTS" ]; then
        for deployment in $DEPLOYMENTS; do
            echo "  Scaling deployment '$deployment' back to 1 replica"
            kubectl scale deployment "$deployment" --replicas=1 -n "$NAMESPACE"
        done
        echo "✓ All deployments scaled to 1"
    else
        echo "  No deployments found in namespace '$NAMESPACE'"
    fi

    echo ""

    # Suspend all cronjobs
    echo "Restarting ALL  cronjobs..."
    local CRONJOBS=$(kubectl get cronjobs -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

    if [ -n "$CRONJOBS" ]; then
        for cronjob in $CRONJOBS; do
            echo "  Suspending cronjob '$cronjob'"
            kubectl patch cronjob "$cronjob" -n "$NAMESPACE" -p '{"spec":{"suspend":false}}'
        done
        echo "✓ All cronjobs suspended"
    else
        echo "  No cronjobs found in namespace '$NAMESPACE'"
    fi

    echo ""
    echo "=========================================="
    echo "Scale up complete for namespace: $NAMESPACE"

    # Optional: Show current status
    echo ""
    echo "Current status:"
    echo "Deployments:"
    kubectl get deployments -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas,READY:.status.readyReplicas 2>/dev/null || echo "  No
 deployments found"

    echo ""
    echo "CronJobs:"
    kubectl get cronjobs -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,SUSPENDED:.spec.suspend 2>/dev/null || echo "  No cronjobs found"
}

# Call the function with argument passed to the script
scaleup-namespace "$1"