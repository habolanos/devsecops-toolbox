"""
Mock utilities para Amazon Web Services (AWS) API
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


class AWSMock:
    """Mock para servicios de AWS."""
    
    def __init__(self):
        self.regions = ["us-east-1", "us-west-2", "eu-west-1"]
        self.accounts = []
        self.iam_users = []
        self.ec2_instances = []
        self.rds_instances = []
        self.s3_buckets = []
        self.lambda_functions = []
        self.eks_clusters = []
    
    def mock_sts_caller_identity(self) -> Dict[str, Any]:
        """Retorna respuesta mock de STS GetCallerIdentity."""
        return {
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test-user"
        }
    
    def mock_iam_user_response(self, user_name: str = "test-user") -> Dict[str, Any]:
        """Retorna respuesta mock de usuario IAM."""
        return {
            "User": {
                "Path": "/",
                "UserName": user_name,
                "UserId": "AIDACKCEVSQ6C2EXAMPLE",
                "Arn": f"arn:aws:iam::123456789012:user/{user_name}",
                "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "PasswordLastUsed": datetime(2024, 1, 15, tzinfo=timezone.utc),
                "Tags": [
                    {"Key": "Environment", "Value": "Test"},
                    {"Key": "Team", "Value": "DevOps"}
                ]
            }
        }
    
    def mock_iam_role_response(self, role_name: str = "test-role") -> Dict[str, Any]:
        """Retorna respuesta mock de rol IAM."""
        return {
            "Role": {
                "Path": "/",
                "RoleName": role_name,
                "RoleId": "AROA1234567890EXAMPLE",
                "Arn": f"arn:aws:iam::123456789012:role/{role_name}",
                "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                "Description": f"Test role {role_name}",
                "MaxSessionDuration": 3600,
                "Tags": [
                    {"Key": "Environment", "Value": "Test"}
                ]
            }
        }
    
    def mock_ec2_instance_response(self, 
                                    instance_id: str = "i-1234567890abcdef0",
                                    state: str = "running") -> Dict[str, Any]:
        """Retorna respuesta mock de instancia EC2."""
        return {
            "InstanceId": instance_id,
            "ImageId": "ami-12345678",
            "InstanceType": "t3.medium",
            "KeyName": "test-keypair",
            "LaunchTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "Monitoring": {"State": "disabled"},
            "Placement": {
                "AvailabilityZone": "us-east-1a",
                "Tenancy": "default"
            },
            "PrivateDnsName": "ip-10-0-0-1.ec2.internal",
            "PrivateIpAddress": "10.0.0.1",
            "PublicDnsName": "ec2-203-0-113-1.compute-1.amazonaws.com",
            "PublicIpAddress": "203.0.113.1",
            "State": {
                "Code": 16 if state == "running" else 80 if state == "stopped" else 48,
                "Name": state
            },
            "SubnetId": "subnet-12345678",
            "VpcId": "vpc-12345678",
            "Architecture": "x86_64",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "AttachTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
                        "DeleteOnTermination": True,
                        "Status": "attached",
                        "VolumeId": "vol-12345678"
                    }
                }
            ],
            "EbsOptimized": False,
            "EnaSupport": True,
            "Hypervisor": "xen",
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-12345678",
                    "PrivateIpAddress": "10.0.0.1",
                    "PrivateIpAddresses": [
                        {
                            "Primary": True,
                            "PrivateIpAddress": "10.0.0.1"
                        }
                    ],
                    "SubnetId": "subnet-12345678",
                    "VpcId": "vpc-12345678"
                }
            ],
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SecurityGroups": [
                {"GroupId": "sg-12345678", "GroupName": "test-sg"}
            ],
            "SourceDestCheck": True,
            "Tags": [
                {"Key": "Name", "Value": f"test-instance-{instance_id[-8:]}"},
                {"Key": "Environment", "Value": "Test"}
            ],
            "VirtualizationType": "hvm",
            "CpuOptions": {
                "CoreCount": 2,
                "ThreadsPerCore": 2
            }
        }
    
    def mock_rds_instance_response(self,
                                    db_instance_id: str = "test-db-instance") -> Dict[str, Any]:
        """Retorna respuesta mock de instancia RDS."""
        return {
            "DBInstanceIdentifier": db_instance_id,
            "DBInstanceClass": "db.t3.medium",
            "Engine": "postgres",
            "EngineVersion": "15.4",
            "DBInstanceStatus": "available",
            "MasterUsername": "admin",
            "DBName": "testdatabase",
            "Endpoint": {
                "Address": f"{db_instance_id}.abc123xyz789.us-east-1.rds.amazonaws.com",
                "Port": 5432,
                "HostedZoneId": "Z2R2ITUGPM61AM"
            },
            "AllocatedStorage": 100,
            "InstanceCreateTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "PreferredBackupWindow": "03:00-04:00",
            "BackupRetentionPeriod": 7,
            "DBSecurityGroups": [],
            "VpcSecurityGroups": [
                {"VpcSecurityGroupId": "sg-12345678", "Status": "active"}
            ],
            "DBParameterGroups": [
                {"DBParameterGroupName": "default.postgres15", "ParameterApplyStatus": "in-sync"}
            ],
            "AvailabilityZone": "us-east-1a",
            "DBSubnetGroup": {
                "DBSubnetGroupName": "test-subnet-group",
                "DBSubnetGroupDescription": "Test subnet group",
                "VpcId": "vpc-12345678",
                "SubnetGroupStatus": "Complete",
                "Subnets": [
                    {
                        "SubnetIdentifier": "subnet-12345678",
                        "SubnetAvailabilityZone": {"Name": "us-east-1a"},
                        "SubnetStatus": "Active"
                    }
                ]
            },
            "PreferredMaintenanceWindow": "mon:04:00-mon:05:00",
            "PendingModifiedValues": {},
            "MultiAZ": False,
            "LicenseModel": "postgresql-license",
            "StorageType": "gp2",
            "DbInstancePort": 0,
            "StorageEncrypted": True,
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            "DbiResourceId": "db-ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX234YZ",
            "CACertificateIdentifier": "rds-ca-2019",
            "DomainMemberships": [],
            "CopyTagsToSnapshot": True,
            "MonitoringInterval": 0,
            "DBInstanceArn": f"arn:aws:rds:us-east-1:123456789012:db:{db_instance_id}",
            "IAMDatabaseAuthenticationEnabled": False,
            "PerformanceInsightsEnabled": False,
            "DeletionProtection": False,
            "AssociatedRoles": [],
            "TagList": [
                {"Key": "Environment", "Value": "Test"},
                {"Key": "Team", "Value": "DevOps"}
            ]
        }
    
    def mock_s3_bucket_response(self, bucket_name: str = "test-bucket") -> Dict[str, Any]:
        """Retorna respuesta mock de bucket S3."""
        return {
            "Name": bucket_name,
            "CreationDate": datetime(2024, 1, 1, tzinfo=timezone.utc)
        }
    
    def mock_s3_bucket_details(self, bucket_name: str = "test-bucket") -> Dict[str, Any]:
        """Retorna detalles de bucket S3."""
        return {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Buckets": [
                {"Name": bucket_name, "CreationDate": datetime(2024, 1, 1, tzinfo=timezone.utc)}
            ],
            "Owner": {
                "DisplayName": "test-user",
                "ID": "123456789012abcdef123456789012abcdef123456789012abcdef1234567890"
            }
        }
    
    def mock_lambda_function_response(self,
                                       function_name: str = "test-function") -> Dict[str, Any]:
        """Retorna respuesta mock de función Lambda."""
        return {
            "FunctionName": function_name,
            "FunctionArn": f"arn:aws:lambda:us-east-1:123456789012:function:{function_name}",
            "Runtime": "python3.11",
            "Role": "arn:aws:iam::123456789012:role/lambda-role",
            "Handler": "lambda_function.handler",
            "CodeSize": 1024,
            "Description": f"Test lambda function {function_name}",
            "Timeout": 30,
            "MemorySize": 128,
            "LastModified": "2024-01-01T00:00:00.000+0000",
            "CodeSha256": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567abc890def123=",
            "Version": "$LATEST",
            "Environment": {
                "Variables": {
                    "ENV": "test",
                    "LOG_LEVEL": "INFO"
                }
            },
            "TracingConfig": {"Mode": "PassThrough"},
            "RevisionId": "12345678-1234-1234-1234-123456789012",
            "State": "Active",
            "LastUpdateStatus": "Successful",
            "PackageType": "Zip",
            "Architectures": ["x86_64"],
            "EphemeralStorage": {"Size": 512},
            "SnapStart": {"ApplyOn": "None", "OptimizationStatus": "Off"},
            "LoggingConfig": {
                "LogFormat": "Text",
                "LogGroup": f"/aws/lambda/{function_name}"
            }
        }
    
    def mock_eks_cluster_response(self, cluster_name: str = "test-cluster") -> Dict[str, Any]:
        """Retorna respuesta mock de cluster EKS."""
        return {
            "cluster": {
                "name": cluster_name,
                "arn": f"arn:aws:eks:us-east-1:123456789012:cluster/{cluster_name}",
                "createdAt": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "version": "1.28",
                "endpoint": f"https://ABC123DEF456.yl4.us-east-1.eks.amazonaws.com",
                "roleArn": "arn:aws:iam::123456789012:role/eks-cluster-role",
                "resourcesVpcConfig": {
                    "subnetIds": [
                        "subnet-12345678",
                        "subnet-87654321",
                        "subnet-abcdef12"
                    ],
                    "securityGroupIds": ["sg-12345678"],
                    "vpcId": "vpc-12345678",
                    "endpointPublicAccess": True,
                    "endpointPrivateAccess": False,
                    "publicAccessCidrs": ["0.0.0.0/0"]
                },
                "kubernetesNetworkConfig": {
                    "serviceIpv4Cidr": "172.20.0.0/16",
                    "ipFamily": "ipv4"
                },
                "logging": {
                    "clusterLogging": [
                        {
                            "types": ["api", "audit", "authenticator", "controllerManager", "scheduler"],
                            "enabled": False
                        }
                    ]
                },
                "identity": {
                    "oidc": {
                        "issuer": f"https://oidc.eks.us-east-1.amazonaws.com/id/ABC123DEF456GHI789JKLM012NOP345QRS678TUV901WXY234ZAB567CDE890FGH123"
                    }
                },
                "status": "ACTIVE",
                "certificateAuthority": {
                    "data": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUM..."
                },
                "platformVersion": "eks.5",
                "tags": {
                    "Environment": "Test",
                    "Team": "DevOps"
                },
                "health": {
                    "issues": []
                },
                "encryptionConfig": []
            }
        }
    
    def mock_vpc_response(self, vpc_id: str = "vpc-12345678") -> Dict[str, Any]:
        """Retorna respuesta mock de VPC."""
        return {
            "VpcId": vpc_id,
            "OwnerId": "123456789012",
            "State": "available",
            "CidrBlock": "10.0.0.0/16",
            "DhcpOptionsId": "dopt-12345678",
            "InstanceTenancy": "default",
            "IsDefault": False,
            "Tags": [
                {"Key": "Name", "Value": "test-vpc"},
                {"Key": "Environment", "Value": "Test"}
            ],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-12345678",
                    "CidrBlock": "10.0.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ]
        }
    
    def mock_security_group_response(self, sg_id: str = "sg-12345678") -> Dict[str, Any]:
        """Retorna respuesta mock de Security Group."""
        return {
            "GroupId": sg_id,
            "GroupName": "test-sg",
            "Description": "Test security group",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 80,
                    "ToPort": 80,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP"}]
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS"}]
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "10.0.0.0/8", "Description": "SSH"}]
                }
            ],
            "IpPermissionsEgress": [
                {
                    "IpProtocol": "-1",
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
                }
            ],
            "VpcId": "vpc-12345678",
            "Tags": [
                {"Key": "Name", "Value": "test-sg"},
                {"Key": "Environment", "Value": "Test"}
            ]
        }
    
    def mock_acm_certificate_response(self, cert_arn: str = "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012") -> Dict[str, Any]:
        """Retorna respuesta mock de certificado ACM."""
        return {
            "CertificateArn": cert_arn,
            "DomainName": "example.com",
            "SubjectAlternativeNames": ["example.com", "www.example.com"],
            "DomainValidationOptions": [
                {
                    "DomainName": "example.com",
                    "ValidationDomain": "example.com",
                    "ValidationStatus": "SUCCESS",
                    "ResourceRecord": {
                        "Name": "_abc123def456.example.com.",
                        "Type": "CNAME",
                        "Value": "_xyz789abc012.acm-validations.aws."
                    },
                    "ValidationMethod": "DNS"
                }
            ],
            "Serial": "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00",
            "Subject": "CN=example.com",
            "Issuer": "Amazon",
            "CreatedAt": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "Status": "ISSUED",
            "Type": "AMAZON_ISSUED",
            "KeyAlgorithm": "RSA-2048",
            "KeyUsages": ["DIGITAL_SIGNATURE", "KEY_ENCIPHERMENT"],
            "ExtendedKeyUsages": ["TLS_WEB_SERVER_AUTHENTICATION", "TLS_WEB_CLIENT_AUTHENTICATION"],
            "InUseBy": [
                f"arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/50dc6c495c0c9188"
            ],
            "RenewalEligibility": "INELIGIBLE",
            "NotBefore": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "NotAfter": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "Tags": [
                {"Key": "Environment", "Value": "Test"}
            ]
        }
    
    def mock_error_response(self, error_code: str = "AccessDenied", 
                           message: str = "Access denied") -> Dict[str, Any]:
        """Retorna respuesta de error de AWS API."""
        return {
            "Error": {
                "Code": error_code,
                "Message": message
            },
            "ResponseMetadata": {
                "HTTPStatusCode": 403 if error_code == "AccessDenied" else 400
            }
        }
    
    def create_mock_boto3_client(self, service_name: str) -> MagicMock:
        """Crea un cliente mock de boto3."""
        mock_client = MagicMock()
        
        if service_name == "sts":
            mock_client.get_caller_identity.return_value = self.mock_sts_caller_identity()
        
        elif service_name == "iam":
            mock_client.get_user.return_value = self.mock_iam_user_response()
            mock_client.get_role.return_value = self.mock_iam_role_response()
            mock_client.list_users.return_value = {"Users": [self.mock_iam_user_response()["User"]]}
            mock_client.list_roles.return_value = {"Roles": [self.mock_iam_role_response()["Role"]]}
        
        elif service_name == "ec2":
            mock_client.describe_instances.return_value = {
                "Reservations": [{"Instances": [self.mock_ec2_instance_response()]}]
            }
            mock_client.describe_vpcs.return_value = {"Vpcs": [self.mock_vpc_response()]}
            mock_client.describe_security_groups.return_value = {
                "SecurityGroups": [self.mock_security_group_response()]
            }
        
        elif service_name == "rds":
            mock_client.describe_db_instances.return_value = {
                "DBInstances": [self.mock_rds_instance_response()]
            }
        
        elif service_name == "s3":
            mock_client.list_buckets.return_value = self.mock_s3_bucket_details()
            mock_client.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}
        
        elif service_name == "lambda":
            mock_client.get_function.return_value = {
                "Configuration": self.mock_lambda_function_response()
            }
            mock_client.list_functions.return_value = {
                "Functions": [self.mock_lambda_function_response()]
            }
        
        elif service_name == "eks":
            mock_client.describe_cluster.return_value = self.mock_eks_cluster_response()
            mock_client.list_clusters.return_value = {"clusters": ["test-cluster"]}
        
        elif service_name == "acm":
            mock_client.describe_certificate.return_value = {
                "Certificate": self.mock_acm_certificate_response()
            }
            mock_client.list_certificates.return_value = {
                "CertificateSummaryList": [
                    {
                        "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012",
                        "DomainName": "example.com"
                    }
                ]
            }
        
        elif service_name == "cloudwatch":
            mock_client.describe_alarms.return_value = {
                "MetricAlarms": [
                    {
                        "AlarmName": "test-alarm",
                        "AlarmArn": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:test-alarm",
                        "StateValue": "OK",
                        "MetricName": "CPUUtilization",
                        "Namespace": "AWS/EC2",
                        "Statistic": "Average",
                        "Threshold": 80.0,
                        "ComparisonOperator": "GreaterThanThreshold",
                        "EvaluationPeriods": 2
                    }
                ]
            }
        
        return mock_client


class AWSCLIMock:
    """Mock para comandos AWS CLI."""
    
    def __init__(self):
        self.commands = {}
        self._setup_default_commands()
    
    def _setup_default_commands(self):
        """Configura comandos mock por defecto."""
        aws_mock = AWSMock()
        
        self.commands = {
            "sts get-caller-identity": (0, json.dumps(aws_mock.mock_sts_caller_identity()), ""),
            "configure list": (0, """profile                test-profile
region                us-east-1
output                json
""", ""),
            "ec2 describe-instances": (0, json.dumps({"Reservations": [{"Instances": [aws_mock.mock_ec2_instance_response()]}]}), ""),
            "rds describe-db-instances": (0, json.dumps({"DBInstances": [aws_mock.mock_rds_instance_response()]}), ""),
            "s3api list-buckets": (0, json.dumps(aws_mock.mock_s3_bucket_details()), ""),
            "lambda list-functions": (0, json.dumps({"Functions": [aws_mock.mock_lambda_function_response()]}), ""),
            "eks list-clusters": (0, json.dumps({"clusters": ["test-cluster"]}), ""),
        }
    
    def get_command_response(self, command: str) -> tuple:
        """Retorna respuesta mock para comando AWS CLI."""
        for cmd_pattern, response in self.commands.items():
            if cmd_pattern in command:
                return response
        
        # Default: éxito vacío
        return (0, "{}", "")
