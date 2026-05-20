output "victim_public_ips" {
  value = { for k, v in aws_instance.victim_node : k => v.public_ip }
}

output "victim_private_ips" {
  value = { for k, v in aws_instance.victim_node : k => v.private_ip }
}

output "ids_public_ip" {
  value = aws_eip.ids_eip.public_ip
}

output "soc_public_ip" {
  value = aws_eip.soc_eip.public_ip
}

output "kali_public_ip" {
  value = aws_instance.kali_attack.public_ip
}

output "sqs_queue_url" {
  value = aws_sqs_queue.flow_queue.id
}

output "s3_bucket_name" {
  value = aws_s3_bucket.models_bucket.id
}
