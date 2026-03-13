#!/usr/bin/env python3
"""Check what instance type is configured for training in the state machine."""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    
    sfn_client = boto3.client('stepfunctions', region_name=region)
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:MovieLensMLPipeline"
    
    print("\n" + "="*70)
    print("CHECKING TRAINING CONFIGURATION")
    print("="*70)
    print()
    
    response = sfn_client.describe_state_machine(
        stateMachineArn=state_machine_arn
    )
    
    definition = json.loads(response['definition'])
    
    if 'ModelTraining' in definition['States']:
        training_state = definition['States']['ModelTraining']
        
        print("ModelTraining State Configuration:")
        print()
        
        if 'Parameters' in training_state:
            params = training_state['Parameters']
            
            if 'ResourceConfig' in params:
                resource_config = params['ResourceConfig']
                print("ResourceConfig:")
                print(f"  InstanceType: {resource_config.get('InstanceType', 'NOT SET')}")
                print(f"  InstanceCount: {resource_config.get('InstanceCount', 'NOT SET')}")
                print(f"  VolumeSizeInGB: {resource_config.get('VolumeSizeInGB', 'NOT SET')}")
                print()
            
            if 'AlgorithmSpecification' in params:
                algo_spec = params['AlgorithmSpecification']
                print("AlgorithmSpecification:")
                print(f"  TrainingImage: {algo_spec.get('TrainingImage', 'NOT SET')}")
                print()
        
        print("Resource ARN:")
        print(f"  {training_state.get('Resource', 'NOT SET')}")
        print()
        
        # Check if it has .sync
        resource = training_state.get('Resource', '')
        if '.sync' in resource:
            print("[OK] Training uses .sync (will wait for completion)")
        else:
            print("[!] WARNING: Training does NOT use .sync (won't wait)")
    
    print()
    print("="*70)

if __name__ == "__main__":
    main()
