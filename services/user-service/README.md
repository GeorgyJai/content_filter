# User Service

User Service is responsible for managing user profiles, preferences, and subscriptions to content sources.

## Features

- User creation and management
- User profile and preferences storage
- Content source management
- Subscription management (add/remove/list)
- gRPC API for inter-service communication

## Architecture

The service is built using:
- **Python 3.11+**: Core language
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Database
- **gRPC**: Inter-service communication protocol

## Database Models

### User
- `user_id`: Primary key
- `username`: User's username
- `platform`: Platform identifier (telegram, etc.)
- `created_at`: Creation timestamp

### UserProfile
- `profile_id`: Primary key
- `user_id`: Foreign key to User
- `preferences`: JSON field for user preferences
- `updated_at`: Last update timestamp

### ContentSource
- `source_id`: Primary key
- `platform_type`: Platform type (telegram, vk, youtube)
- `url`: Source URL (unique)
- `topic`: Optional topic
- `publish_frequency`: Optional frequency

### Subscription
- `subscription_id`: Primary key
- `user_id`: Foreign key to User
- `source_id`: Foreign key to ContentSource
- `subscribed_at`: Subscription timestamp

## gRPC API

### CreateUser
Creates a new user with default profile.

**Request:**
```protobuf
message CreateUserRequest {
    string username = 1;
    string platform = 2;
}
```

**Response:**
```protobuf
message UserResponse {
    int32 user_id = 1;
    string username = 2;
    string platform = 3;
}
```

### GetUserProfile
Retrieves user profile and preferences.

**Request:**
```protobuf
message GetUserProfileRequest {
    int32 user_id = 1;
}
```

**Response:**
```protobuf
message UserProfileResponse {
    int32 profile_id = 1;
    int32 user_id = 2;
    string preferences_json = 3;
    string updated_at = 4;
}
```

### UpdateUserPreferences
Updates user preferences.

**Request:**
```protobuf
message UpdatePreferencesRequest {
    int32 user_id = 1;
    string preferences_json = 2;
}
```

### AddSubscription
Adds a subscription to a content source.

**Request:**
```protobuf
message AddSubscriptionRequest {
    int32 user_id = 1;
    string source_url = 2;
    string platform_type = 3;
}
```

**Response:**
```protobuf
message SubscriptionResponse {
    int32 subscription_id = 1;
    bool success = 2;
    string message = 3;
}
```

### RemoveSubscription
Removes a subscription.

**Request:**
```protobuf
message RemoveSubscriptionRequest {
    int32 user_id = 1;
    int32 source_id = 2;
}
```

### GetUserSubscriptions
Gets all subscriptions for a user.

**Request:**
```protobuf
message GetSubscriptionsRequest {
    int32 user_id = 1;
}
```

**Response:**
```protobuf
message SubscriptionsListResponse {
    repeated Subscription subscriptions = 1;
}
```

## Configuration

Configuration is managed through environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `SQL_ECHO`: Enable SQL query logging (true/false)
- `GRPC_PORT`: gRPC server port (default: 50051)
- `GRPC_MAX_WORKERS`: Maximum worker threads (default: 10)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Running the Service

### Using Docker

```bash
docker build -t user-service .
docker run -p 50051:50051 --env-file .env user-service
```

### Using Docker Compose

The service is included in the main `docker-compose.yml` file.

```bash
docker-compose up user-service
```

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Generate gRPC code:
```bash
python -m grpc_tools.protoc \
    -I../../shared/proto \
    --python_out=. \
    --grpc_python_out=. \
    ../../shared/proto/user_service.proto
```

3. Set environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the service:
```bash
python main.py
```

## Testing

Run unit tests:
```bash
pytest tests/
```

## Dependencies

See [`requirements.txt`](requirements.txt) for a complete list of dependencies.

## License

Part of the Content Filter System project.
