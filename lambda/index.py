# lambda/index.py
import json
import os
import urllib.request

# FastAPIエンドポイント指定
FASTAPI_ENDPOINT = os.environ.get("FASTAPI_ENDPOINT", "https://11f5-35-198-228-94.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })

        # FastAPIサーバーにリクエストを送る
        prompt = ""
        for msg in messages:
            if msg["role"] == "user":
                prompt += f"User: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"Assistant: {msg['content']}\n"
        prompt += "Assistant: "

        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        print("Calling FastAPI endpoint with payload:", json.dumps(request_payload))

        # JSONにエンコード
        data = json.dumps(request_payload).encode("utf-8")

        # HTTPリクエストを作成
        req = urllib.request.Request(
            FASTAPI_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # リクエスト送信
        with urllib.request.urlopen(req, timeout=100) as response:
            theHttpStatus = response.getcode()
            if theHttpStatus != 200:
                raise Exception(f"FastAPI server returned error status: {theHttpStatus}")
            
            res_body = response.read()
            if not res_body:
                raise Exception("Empty response from FastAPI server")
            
            res_text = res_body.decode("utf-8")
            response_body = json.loads(res_text)

        print("FastAPI response:", json.dumps(response_body, default=str))

        # if fastapi_response.status_code != 200:
        #     raise Exception(f"FastAPI server error: {fastapi_response.text}")

        # response_body = fastapi_response.json()
        # print("FastAPI response:", json.dumps(response_body, default=str))

        # 応答の検証
        if 'generated_text' not in response_body:
            raise Exception("No generated_text in the response from FastAPI server")

        assistant_response = response_body['generated_text']

        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
