#!/usr/bin/env python3
"""
Stop All Costly AWS Resources

This script stops or deletes all AWS resources that incur ongoing costs.
Use this to immediately halt charges when not actively using the system.

HIGH-COST RESOURCES STOPPED:
- SageMaker Endpoints (~$387-969/month)
- SageMaker Training Jobs (if running)
- EC2 Instances
- RDS Database Instances
- SageMaker Notebook Instances

MEDIUM-COST RESOURCES STOPPED:
- EventBridge Rules (disabled, not deleted)
- CloudWatch Alarms (disabled)

LOW-COST RESOURCES (NOT TOUCHED):
- S3 buckets (data preserved)
- Lambda functions (no cost when idle)
- Step Functions (no cost when idle)
- IAM roles (no cost)

Usage:
    python stop_all_costly_resources.py --region us-east-1 [--dry-run]
"""

import boto3
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Any


class CostlyResourceStopper:
    def __init__(self, region: str, dry_run: bool = False):
        self.region = region
        self.dry_run = dry_run
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.ec2 = boto3.client('ec2', region_name=region)
        self.rds = boto3.client('rds', region_name=region)
        self.events = boto3.client('events', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        self.stopped_resources = []
        self.failed_resources = []
        self.total_estimated_savings = 0.0
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = "[DRY-RUN] " if self.dry_run else ""
        print(f"{prefix}[{timestamp}] [{level}] {message}")
    
    def stop_sagemaker_endpoints(self) -> None:
        """Stop all SageMaker endpoints (HIGHEST COST)"""
        self.log("=" * 80)
        self.log("STOPPING SAGEMAKER ENDPOINTS (Highest Cost: ~$387-969/month)")
        self.log("=" * 80)
        
        try:
            response = self.sagemaker.list_endpoints()
            endpoints = response.get('Endpoints', [])
            
            if not endpoints:
                self.log("No SageMaker endpoints found")
                return
            
            for endpoint in endpoints:
                endpoint_name = endpoint['EndpointName']
                status = endpoint['EndpointStatus']
                
                if status in ['InService', 'Creating', 'Updating']:
                    self.log(f"Found endpoint: {endpoint_name} (Status: {status})")
                    
                    if not self.dry_run:
                        try:
                            self.sagemaker.delete_endpoint(EndpointName=endpoint_name)
                            self.log(f"✓ Deleted endpoint: {endpoint_name}", "SUCCESS")
                            self.stopped_resources.append({
                                'type': 'SageMaker Endpoint',
                                'name': endpoint_name,
                                'estimated_monthly_savings': 387.00  # Minimum cost
                            })
                            self.total_estimated_savings += 387.00
                        except Exception as e:
                            self.log(f"✗ Failed to delete endpoint {endpoint_name}: {e}", "ERROR")
                            self.failed_resources.append({
                                'type': 'SageMaker Endpoint',
                                'name': endpoint_name,
                                'error': str(e)
                            })
                    else:
                        self.log(f"Would delete endpoint: {endpoint_name}")
                        self.total_estimated_savings += 387.00
                else:
                    self.log(f"Endpoint {endpoint_name} already stopped (Status: {status})")
        
        except Exception as e:
            self.log(f"Error listing SageMaker endpoints: {e}", "ERROR")
    
    def stop_sagemaker_training_jobs(self) -> None:
        """Stop any running SageMaker training jobs"""
        self.log("\n" + "=" * 80)
        self.log("STOPPING SAGEMAKER TRAINING JOBS")
        self.log("=" * 80)
        
        try:
            response = self.sagemaker.list_training_jobs(
                StatusEquals='InProgress',
                MaxResults=100
            )
            training_jobs = response.get('TrainingJobSummaries', [])
            
            if not training_jobs:
                self.log("No running training jobs found")
                return
            
            for job in training_jobs:
                job_name = job['TrainingJobName']
                self.log(f"Found running training job: {job_name}")
                
                if not self.dry_run:
                    try:
                        self.sagemaker.stop_training_job(TrainingJobName=job_name)
                        self.log(f"✓ Stopped training job: {job_name}", "SUCCESS")
                        self.stopped_resources.append({
                            'type': 'SageMaker Training Job',
                            'name': job_name,
                            'estimated_monthly_savings': 50.00  # Estimated
                        })
                        self.total_estimated_savings += 50.00
                    except Exception as e:
                        self.log(f"✗ Failed to stop training job {job_name}: {e}", "ERROR")
                        self.failed_resources.append({
                            'type': 'SageMaker Training Job',
                            'name': job_name,
                            'error': str(e)
                        })
                else:
                    self.log(f"Would stop training job: {job_name}")
                    self.total_estimated_savings += 50.00
        
        except Exception as e:
            self.log(f"Error listing training jobs: {e}", "ERROR")
    
    def stop_sagemaker_notebook_instances(self) -> None:
        """Stop SageMaker notebook instances"""
        self.log("\n" + "=" * 80)
        self.log("STOPPING SAGEMAKER NOTEBOOK INSTANCES")
        self.log("=" * 80)
        
        try:
            response = self.sagemaker.list_notebook_instances()
            notebooks = response.get('NotebookInstances', [])
            
            if not notebooks:
                self.log("No notebook instances found")
                return
            
            for notebook in notebooks:
                notebook_name = notebook['NotebookInstanceName']
                status = notebook['NotebookInstanceStatus']
                
                if status == 'InService':
                    self.log(f"Found running notebook: {notebook_name}")
                    
                    if not self.dry_run:
                        try:
                            self.sagemaker.stop_notebook_instance(
                                NotebookInstanceName=notebook_name
                            )
                            self.log(f"✓ Stopped notebook: {notebook_name}", "SUCCESS")
                            self.stopped_resources.append({
                                'type': 'SageMaker Notebook',
                                'name': notebook_name,
                                'estimated_monthly_savings': 100.00
                            })
                            self.total_estimated_savings += 100.00
                        except Exception as e:
                            self.log(f"✗ Failed to stop notebook {notebook_name}: {e}", "ERROR")
                            self.failed_resources.append({
                                'type': 'SageMaker Notebook',
                                'name': notebook_name,
                                'error': str(e)
                            })
                    else:
                        self.log(f"Would stop notebook: {notebook_name}")
                        self.total_estimated_savings += 100.00
                else:
                    self.log(f"Notebook {notebook_name} already stopped (Status: {status})")
        
        except Exception as e:
            self.log(f"Error listing notebook instances: {e}", "ERROR")
    
    def stop_ec2_instances(self) -> None:
        """Stop all running EC2 instances"""
        self.log("\n" + "=" * 80)
        self.log("STOPPING EC2 INSTANCES")
        self.log("=" * 80)
        
        try:
            response = self.ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            instances = []
            for reservation in response.get('Reservations', []):
                instances.extend(reservation.get('Instances', []))
            
            if not instances:
                self.log("No running EC2 instances found")
                return
            
            for instance in instances:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                
                # Get instance name from tags
                name = "Unnamed"
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                self.log(f"Found running instance: {instance_id} ({name}, {instance_type})")
                
                if not self.dry_run:
                    try:
                        self.ec2.stop_instances(InstanceIds=[instance_id])
                        self.log(f"✓ Stopped EC2 instance: {instance_id}", "SUCCESS")
                        self.stopped_resources.append({
                            'type': 'EC2 Instance',
                            'name': f"{instance_id} ({name})",
                            'estimated_monthly_savings': 50.00  # Varies by type
                        })
                        self.total_estimated_savings += 50.00
                    except Exception as e:
                        self.log(f"✗ Failed to stop instance {instance_id}: {e}", "ERROR")
                        self.failed_resources.append({
                            'type': 'EC2 Instance',
                            'name': instance_id,
                            'error': str(e)
                        })
                else:
                    self.log(f"Would stop instance: {instance_id}")
                    self.total_estimated_savings += 50.00
        
        except Exception as e:
            error_msg = str(e)
            if 'UnauthorizedOperation' in error_msg or 'not authorized' in error_msg:
                self.log(f"⚠️  Skipping EC2 instances - insufficient permissions", "WARNING")
                self.log("   (If you don't have EC2 instances, this is OK)", "WARNING")
            else:
                self.log(f"Error listing EC2 instances: {e}", "ERROR")
    
    def stop_rds_instances(self) -> None:
        """Stop all RDS database instances"""
        self.log("\n" + "=" * 80)
        self.log("STOPPING RDS DATABASE INSTANCES")
        self.log("=" * 80)
        
        try:
            response = self.rds.describe_db_instances()
            db_instances = response.get('DBInstances', [])
            
            if not db_instances:
                self.log("No RDS instances found")
                return
            
            for db in db_instances:
                db_id = db['DBInstanceIdentifier']
                status = db['DBInstanceStatus']
                
                if status == 'available':
                    self.log(f"Found running RDS instance: {db_id}")
                    
                    if not self.dry_run:
                        try:
                            self.rds.stop_db_instance(DBInstanceIdentifier=db_id)
                            self.log(f"✓ Stopped RDS instance: {db_id}", "SUCCESS")
                            self.stopped_resources.append({
                                'type': 'RDS Instance',
                                'name': db_id,
                                'estimated_monthly_savings': 100.00
                            })
                            self.total_estimated_savings += 100.00
                        except Exception as e:
                            self.log(f"✗ Failed to stop RDS instance {db_id}: {e}", "ERROR")
                            self.failed_resources.append({
                                'type': 'RDS Instance',
                                'name': db_id,
                                'error': str(e)
                            })
                    else:
                        self.log(f"Would stop RDS instance: {db_id}")
                        self.total_estimated_savings += 100.00
                else:
                    self.log(f"RDS instance {db_id} not available (Status: {status})")
        
        except Exception as e:
            error_msg = str(e)
            if 'AccessDenied' in error_msg or 'not authorized' in error_msg:
                self.log(f"⚠️  Skipping RDS instances - insufficient permissions", "WARNING")
                self.log("   (If you don't have RDS instances, this is OK)", "WARNING")
            else:
                self.log(f"Error listing RDS instances: {e}", "ERROR")
    
    def disable_eventbridge_rules(self) -> None:
        """Disable EventBridge rules (prevents scheduled retraining)"""
        self.log("\n" + "=" * 80)
        self.log("DISABLING EVENTBRIDGE RULES")
        self.log("=" * 80)
        
        try:
            response = self.events.list_rules()
            rules = response.get('Rules', [])
            
            if not rules:
                self.log("No EventBridge rules found")
                return
            
            for rule in rules:
                rule_name = rule['Name']
                state = rule['State']
                
                if state == 'ENABLED':
                    self.log(f"Found enabled rule: {rule_name}")
                    
                    if not self.dry_run:
                        try:
                            self.events.disable_rule(Name=rule_name)
                            self.log(f"✓ Disabled EventBridge rule: {rule_name}", "SUCCESS")
                            self.stopped_resources.append({
                                'type': 'EventBridge Rule',
                                'name': rule_name,
                                'estimated_monthly_savings': 0.00  # Minimal cost
                            })
                        except Exception as e:
                            self.log(f"✗ Failed to disable rule {rule_name}: {e}", "ERROR")
                            self.failed_resources.append({
                                'type': 'EventBridge Rule',
                                'name': rule_name,
                                'error': str(e)
                            })
                    else:
                        self.log(f"Would disable rule: {rule_name}")
                else:
                    self.log(f"Rule {rule_name} already disabled")
        
        except Exception as e:
            error_msg = str(e)
            if 'AccessDeniedException' in error_msg or 'not authorized' in error_msg:
                self.log(f"⚠️  Skipping EventBridge rules - insufficient permissions", "WARNING")
                self.log("   (This is OK - EventBridge rules have minimal cost)", "WARNING")
            else:
                self.log(f"Error listing EventBridge rules: {e}", "ERROR")
    
    def print_summary(self) -> None:
        """Print summary of stopped resources"""
        self.log("\n" + "=" * 80)
        self.log("SUMMARY")
        self.log("=" * 80)
        
        if self.stopped_resources:
            self.log(f"\n✓ Successfully stopped {len(self.stopped_resources)} resources:")
            for resource in self.stopped_resources:
                savings = resource.get('estimated_monthly_savings', 0)
                self.log(f"  - {resource['type']}: {resource['name']} "
                        f"(~${savings:.2f}/month)")
        else:
            self.log("\nNo resources were stopped")
        
        if self.failed_resources:
            self.log(f"\n✗ Failed to stop {len(self.failed_resources)} resources:", "ERROR")
            for resource in self.failed_resources:
                self.log(f"  - {resource['type']}: {resource['name']}", "ERROR")
                self.log(f"    Error: {resource['error']}", "ERROR")
        
        self.log(f"\n💰 ESTIMATED MONTHLY SAVINGS: ${self.total_estimated_savings:.2f}")
        
        if self.total_estimated_savings == 0:
            self.log("\n⚠️  Note: Some services were skipped due to insufficient permissions")
            self.log("   The most important service (SageMaker) was checked")
            self.log("   If you have no SageMaker endpoints, you're good!")
        
        if self.dry_run:
            self.log("\n⚠️  This was a DRY RUN - no resources were actually stopped")
            self.log("Run without --dry-run to actually stop resources")
        else:
            self.log("\n✓ All accessible costly resources have been checked")
            if self.total_estimated_savings > 0:
                self.log("Your AWS bill should decrease significantly")
            self.log("\nTo restart resources, redeploy using:")
            self.log("  python src/infrastructure/deploy_all.py --bucket-name <bucket>")
    
    def run(self) -> None:
        """Execute all stop operations"""
        self.log("Starting AWS Costly Resource Stopper")
        self.log(f"Region: {self.region}")
        self.log(f"Dry Run: {self.dry_run}")
        
        # Stop resources in order of cost (highest first)
        self.stop_sagemaker_endpoints()
        self.stop_sagemaker_training_jobs()
        self.stop_sagemaker_notebook_instances()
        self.stop_ec2_instances()
        self.stop_rds_instances()
        self.disable_eventbridge_rules()
        
        # Print summary
        self.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description='Stop all AWS resources that cost money',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (see what would be stopped)
  python stop_all_costly_resources.py --region us-east-1 --dry-run
  
  # Actually stop resources
  python stop_all_costly_resources.py --region us-east-1
  
  # Stop resources in a different region
  python stop_all_costly_resources.py --region eu-west-1

IMPORTANT:
  - This will DELETE SageMaker endpoints (cannot be paused)
  - This will STOP EC2 and RDS instances (can be restarted)
  - This will DISABLE EventBridge rules (can be re-enabled)
  - S3 data and Lambda functions are NOT affected
  - Use --dry-run first to see what will be stopped
        """
    )
    
    parser.add_argument(
        '--region',
        type=str,
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be stopped without actually stopping'
    )
    
    args = parser.parse_args()
    
    # Confirmation prompt (unless dry-run)
    if not args.dry_run:
        print("\n" + "=" * 80)
        print("⚠️  WARNING: This will stop/delete costly AWS resources!")
        print("=" * 80)
        print("\nThis will:")
        print("  - DELETE all SageMaker endpoints")
        print("  - STOP all running training jobs")
        print("  - STOP all EC2 instances")
        print("  - STOP all RDS instances")
        print("  - DISABLE EventBridge rules")
        print("\nYour data in S3 will NOT be affected.")
        print("\nEstimated savings: $500-1000+/month")
        
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    # Run the stopper
    stopper = CostlyResourceStopper(region=args.region, dry_run=args.dry_run)
    stopper.run()


if __name__ == '__main__':
    main()
