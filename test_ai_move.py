import requests

board = [['.' for _ in range(15)] for _ in range(15)]
board[7][7] = 'A'

rack = ['B', 'A', 'D', 'E', 'F', 'G', 'H']

data = {
    "board": board,
    "rack": rack,
    "score_diff": 0,
    "bag_remaining": 85,
    "ai_type": "random",
    "temperature": 0.5,
    "top_k": 3
}

response = requests.post("http://localhost:5000/api/interactive/ai_move", json=data)
print(response.status_code)
print(response.json())
