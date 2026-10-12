import requests


class APIClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)

    def make_get_request(self, endpoint):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url)
        return response

    # You can add more methods for handling different types of requests (POST, PUT, etc.)

    def close_session(self):
        self.session.close()


# Usage example
if __name__ == "__main__":
    base_url = "https://api.example.com"
    username = "your_username"
    password = "your_password"

    client = APIClient(base_url, username, password)

    try:
        response = client.make_get_request("endpoint_path")
        if response.status_code == 200:
            data = response.json()
            # Process the data as needed
            print(data)
        else:
            print(f"Failed to retrieve data. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request error: {e}")
    finally:
        client.close_session()
