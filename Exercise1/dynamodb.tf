resource "aws_dynamodb_table" "orders" {
    name           = "orders"
    billing_mode   = "PAY_PER_REQUEST"
    hash_key       = "orderID"

    attribute {
        name = "orderID"
        type = "S" # String, matches the exercise's partition key type
    }
    stream_enabled   = true
    stream_view_type = "NEW_AND_OLD_IMAGES"  # matches "View type: New image" from Task 5
}