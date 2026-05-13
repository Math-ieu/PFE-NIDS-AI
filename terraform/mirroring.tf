# 1. Cible du miroir (l'interface réseau de l'IDS)
resource "aws_ec2_traffic_mirror_target" "ids_target" {
  network_interface_id = aws_instance.ids_node.primary_network_interface_id
  description          = "Mirror target to IDS EC2"
}

# 2. Filtre (on capture tout le trafic TCP/UDP)
resource "aws_ec2_traffic_mirror_filter" "all_traffic" {
  description = "Filter all TCP/UDP traffic"
}

resource "aws_ec2_traffic_mirror_filter_rule" "inbound" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.all_traffic.id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_action              = "accept"
  rule_number              = 100
  traffic_direction        = "ingress"
}

resource "aws_ec2_traffic_mirror_filter_rule" "outbound" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.all_traffic.id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_action              = "accept"
  rule_number              = 101
  traffic_direction        = "egress"
}

# 3. Session de miroir (attachée à la victime)
resource "aws_ec2_traffic_mirror_session" "victim_session" {
  network_interface_id     = aws_instance.victim_node.primary_network_interface_id
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.ids_target.id
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.all_traffic.id
  session_number           = 1
  virtual_network_id       = 100
}
