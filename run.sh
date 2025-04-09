mkdir -p /workspace
#curl -X POST http://localhost:8080/generate_recent_news_batch -H "Content-Type: application/json" -d '{"input_filename": "test_cases.txt", "n_rows": 2, "in_parallel": true}' > /workspace/evaluation_response_current.json
curl -X POST https://finance-app-back-end-911835065349.us-central1.run.app/generate_recent_news_batch -H "Content-Type: application/json" -d '{"input_filename": "test_cases.txt", "n_rows": None, "in_parallel": true}' > /workspace/evaluation_response_current.json

cat /workspace/evaluation_response_current.json

# Check if the response contains a final message with status code 200
if ! jq -e 'select(.message_type == "final" and .message.status_code == 200)' /workspace/evaluation_response_current.json > /dev/null; then
    echo "Error: The batch summary generation failed!"
    exit 1
fi

echo "The batch summary was generated successfully!"
