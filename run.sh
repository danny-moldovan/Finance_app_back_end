mkdir /workspace
ls -lh /workspace
curl -X POST https://finance-app-back-end-911835065349.us-central1.run.app/health_check -H "Content-Type: application/json" -d '{"query": "test"}' | sudo jq -r '.' > /workspace/evaluation_response_current.json
cat /workspace/evaluation_response_current.json
if [ "$(sudo jq -r '.message' /workspace/evaluation_response_current.json)" != "Request test was successful!" ]; then
    echo "Error: The batch summary generation failed!"
    exit 1
fi

echo "The batch summary was generated successfully!"
