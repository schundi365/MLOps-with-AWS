"""
Unit tests for auto-scaling configuration.

Tests cover:
- Policy creation
- Configuration validation

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.autoscaling import (
    AutoScalingConfig,
    configure_endpoint_autoscaling
)


class TestAutoScalingConfig:
    """Test AutoScalingConfig class"""
    
    @patch('src.autoscaling.boto3.client')
    def test_init_with_default_parameters(self, mock_boto_client):
        """Test initialization with default parameters"""
        endpoint_name = "test-endpoint"
        
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        # Verify default values (Requirement 6.1)
        assert config.endpoint_name == endpoint_name
        assert config.variant_name == "AllTraffic"
        assert config.min_capacity == 1
        assert config.max_capacity == 5
        assert config.target_value == 70.0
        assert config.scale_out_cooldown == 60
        assert config.scale_in_cooldown == 300
        
        # Verify resource ID format
        assert config.resource_id == f"endpoint/{endpoint_name}/variant/AllTraffic"
    
    @patch('src.autoscaling.boto3.client')
    def test_init_with_custom_parameters(self, mock_boto_client):
        """Test initialization with custom parameters"""
        endpoint_name = "custom-endpoint"
        variant_name = "CustomVariant"
        min_capacity = 2
        max_capacity = 10
        target_value = 100.0
        scale_out_cooldown = 120
        scale_in_cooldown = 600
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            variant_name=variant_name,
            min_capacity=min_capacity,
            max_capacity=max_capacity,
            target_value=target_value,
            scale_out_cooldown=scale_out_cooldown,
            scale_in_cooldown=scale_in_cooldown
        )
        
        # Verify custom values
        assert config.endpoint_name == endpoint_name
        assert config.variant_name == variant_name
        assert config.min_capacity == min_capacity
        assert config.max_capacity == max_capacity
        assert config.target_value == target_value
        assert config.scale_out_cooldown == scale_out_cooldown
        assert config.scale_in_cooldown == scale_in_cooldown
    
    @patch('src.autoscaling.boto3.client')
    def test_resource_id_format(self, mock_boto_client):
        """Test resource ID is correctly formatted"""
        endpoint_name = "my-endpoint"
        variant_name = "MyVariant"
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            variant_name=variant_name
        )
        
        # Verify resource ID format
        expected_resource_id = f"endpoint/{endpoint_name}/variant/{variant_name}"
        assert config.resource_id == expected_resource_id
    
    @patch('src.autoscaling.boto3.client')
    def test_register_scalable_target_success(self, mock_boto_client):
        """Test successful scalable target registration (Requirement 6.1)"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.register_scalable_target.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            min_capacity=1,
            max_capacity=5
        )
        
        response = config.register_scalable_target()
        
        # Verify API call was made with correct parameters
        mock_client.register_scalable_target.assert_called_once_with(
            ServiceNamespace='sagemaker',
            ResourceId=f"endpoint/{endpoint_name}/variant/AllTraffic",
            ScalableDimension='sagemaker:variant:DesiredInstanceCount',
            MinCapacity=1,
            MaxCapacity=5
        )
        
        # Verify response
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    @patch('src.autoscaling.boto3.client')
    def test_register_scalable_target_failure(self, mock_boto_client):
        """Test scalable target registration failure handling"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.register_scalable_target.side_effect = Exception("Registration failed")
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        # Verify exception is raised
        with pytest.raises(Exception, match="Registration failed"):
            config.register_scalable_target()
    
    @patch('src.autoscaling.boto3.client')
    def test_create_scaling_policy_success(self, mock_boto_client):
        """Test successful scaling policy creation (Requirements 6.2, 6.3, 6.4, 6.5)"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.put_scaling_policy.return_value = {
            'PolicyARN': 'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:test',
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        endpoint_name = "test-endpoint"
        target_value = 70.0
        scale_out_cooldown = 60
        scale_in_cooldown = 300
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            target_value=target_value,
            scale_out_cooldown=scale_out_cooldown,
            scale_in_cooldown=scale_in_cooldown
        )
        
        response = config.create_scaling_policy()
        
        # Verify API call was made with correct parameters
        call_args = mock_client.put_scaling_policy.call_args
        assert call_args[1]['PolicyName'] == f"{endpoint_name}-target-tracking-policy"
        assert call_args[1]['ServiceNamespace'] == 'sagemaker'
        assert call_args[1]['ResourceId'] == f"endpoint/{endpoint_name}/variant/AllTraffic"
        assert call_args[1]['ScalableDimension'] == 'sagemaker:variant:DesiredInstanceCount'
        assert call_args[1]['PolicyType'] == 'TargetTrackingScaling'
        
        # Verify target tracking configuration
        target_config = call_args[1]['TargetTrackingScalingPolicyConfiguration']
        assert target_config['TargetValue'] == target_value
        assert target_config['ScaleOutCooldown'] == scale_out_cooldown
        assert target_config['ScaleInCooldown'] == scale_in_cooldown
        
        # Verify predefined metric
        metric_spec = target_config['PredefinedMetricSpecification']
        assert metric_spec['PredefinedMetricType'] == 'SageMakerVariantInvocationsPerInstance'
        
        # Verify response
        assert 'PolicyARN' in response
    
    @patch('src.autoscaling.boto3.client')
    def test_create_scaling_policy_failure(self, mock_boto_client):
        """Test scaling policy creation failure handling"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.put_scaling_policy.side_effect = Exception("Policy creation failed")
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        # Verify exception is raised
        with pytest.raises(Exception, match="Policy creation failed"):
            config.create_scaling_policy()
    
    @patch('src.autoscaling.boto3.client')
    def test_configure_autoscaling_success(self, mock_boto_client):
        """Test complete auto-scaling configuration"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.register_scalable_target.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        mock_client.put_scaling_policy.return_value = {
            'PolicyARN': 'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:test',
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        result = config.configure_autoscaling()
        
        # Verify both API calls were made
        mock_client.register_scalable_target.assert_called_once()
        mock_client.put_scaling_policy.assert_called_once()
        
        # Verify result structure
        assert 'registration' in result
        assert 'policy' in result
        assert result['registration']['ResponseMetadata']['HTTPStatusCode'] == 200
        assert 'PolicyARN' in result['policy']
    
    @patch('src.autoscaling.boto3.client')
    def test_configure_autoscaling_registration_failure(self, mock_boto_client):
        """Test auto-scaling configuration when registration fails"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.register_scalable_target.side_effect = Exception("Registration failed")
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        # Verify exception is raised and policy creation is not attempted
        with pytest.raises(Exception, match="Registration failed"):
            config.configure_autoscaling()
        
        mock_client.put_scaling_policy.assert_not_called()
    
    @patch('src.autoscaling.boto3.client')
    def test_delete_scaling_policy_success(self, mock_boto_client):
        """Test successful scaling policy deletion"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.delete_scaling_policy.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        response = config.delete_scaling_policy()
        
        # Verify API call was made with correct parameters
        mock_client.delete_scaling_policy.assert_called_once_with(
            PolicyName=f"{endpoint_name}-target-tracking-policy",
            ServiceNamespace='sagemaker',
            ResourceId=f"endpoint/{endpoint_name}/variant/AllTraffic",
            ScalableDimension='sagemaker:variant:DesiredInstanceCount'
        )
        
        # Verify response
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    @patch('src.autoscaling.boto3.client')
    def test_deregister_scalable_target_success(self, mock_boto_client):
        """Test successful scalable target deregistration"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.deregister_scalable_target.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        response = config.deregister_scalable_target()
        
        # Verify API call was made with correct parameters
        mock_client.deregister_scalable_target.assert_called_once_with(
            ServiceNamespace='sagemaker',
            ResourceId=f"endpoint/{endpoint_name}/variant/AllTraffic",
            ScalableDimension='sagemaker:variant:DesiredInstanceCount'
        )
        
        # Verify response
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    @patch('src.autoscaling.boto3.client')
    def test_get_scaling_policy_success(self, mock_boto_client):
        """Test successful scaling policy retrieval"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.describe_scaling_policies.return_value = {
            'ScalingPolicies': [
                {
                    'PolicyName': 'test-endpoint-target-tracking-policy',
                    'TargetTrackingScalingPolicyConfiguration': {
                        'TargetValue': 70.0
                    }
                }
            ]
        }
        
        endpoint_name = "test-endpoint"
        config = AutoScalingConfig(endpoint_name=endpoint_name)
        
        response = config.get_scaling_policy()
        
        # Verify API call was made with correct parameters
        mock_client.describe_scaling_policies.assert_called_once_with(
            PolicyNames=[f"{endpoint_name}-target-tracking-policy"],
            ServiceNamespace='sagemaker',
            ResourceId=f"endpoint/{endpoint_name}/variant/AllTraffic",
            ScalableDimension='sagemaker:variant:DesiredInstanceCount'
        )
        
        # Verify response
        assert 'ScalingPolicies' in response
        assert len(response['ScalingPolicies']) == 1


class TestConfigureEndpointAutoscaling:
    """Test convenience function for auto-scaling configuration"""
    
    @patch('src.autoscaling.boto3.client')
    def test_configure_endpoint_autoscaling_with_defaults(self, mock_boto_client):
        """Test convenience function with default parameters"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.register_scalable_target.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        mock_client.put_scaling_policy.return_value = {
            'PolicyARN': 'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:test'
        }
        
        endpoint_name = "test-endpoint"
        
        result = configure_endpoint_autoscaling(endpoint_name=endpoint_name)
        
        # Verify both API calls were made
        mock_client.register_scalable_target.assert_called_once()
        mock_client.put_scaling_policy.assert_called_once()
        
        # Verify result structure
        assert 'registration' in result
        assert 'policy' in result
    
    @patch('src.autoscaling.boto3.client')
    def test_configure_endpoint_autoscaling_with_custom_parameters(self, mock_boto_client):
        """Test convenience function with custom parameters"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.register_scalable_target.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        mock_client.put_scaling_policy.return_value = {
            'PolicyARN': 'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:test'
        }
        
        endpoint_name = "custom-endpoint"
        min_capacity = 2
        max_capacity = 10
        target_value = 100.0
        
        result = configure_endpoint_autoscaling(
            endpoint_name=endpoint_name,
            min_capacity=min_capacity,
            max_capacity=max_capacity,
            target_value=target_value
        )
        
        # Verify registration call with custom parameters
        reg_call_args = mock_client.register_scalable_target.call_args
        assert reg_call_args[1]['MinCapacity'] == min_capacity
        assert reg_call_args[1]['MaxCapacity'] == max_capacity
        
        # Verify policy call with custom target value
        policy_call_args = mock_client.put_scaling_policy.call_args
        target_config = policy_call_args[1]['TargetTrackingScalingPolicyConfiguration']
        assert target_config['TargetValue'] == target_value
        
        # Verify result
        assert 'registration' in result
        assert 'policy' in result


class TestAutoScalingConfigValidation:
    """Test auto-scaling configuration validation"""
    
    @patch('src.autoscaling.boto3.client')
    def test_min_capacity_is_one(self, mock_boto_client):
        """Test minimum capacity is 1 (Requirement 6.1)"""
        endpoint_name = "test-endpoint"
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            min_capacity=1
        )
        
        assert config.min_capacity == 1
    
    @patch('src.autoscaling.boto3.client')
    def test_max_capacity_is_five(self, mock_boto_client):
        """Test maximum capacity is 5 (Requirement 6.1)"""
        endpoint_name = "test-endpoint"
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            max_capacity=5
        )
        
        assert config.max_capacity == 5
    
    @patch('src.autoscaling.boto3.client')
    def test_target_value_is_seventy(self, mock_boto_client):
        """Test target value is 70 invocations per instance (Requirements 6.2, 6.3)"""
        endpoint_name = "test-endpoint"
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            target_value=70.0
        )
        
        assert config.target_value == 70.0
    
    @patch('src.autoscaling.boto3.client')
    def test_scale_out_cooldown_is_sixty_seconds(self, mock_boto_client):
        """Test scale-out cooldown is 60 seconds (Requirement 6.4)"""
        endpoint_name = "test-endpoint"
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            scale_out_cooldown=60
        )
        
        assert config.scale_out_cooldown == 60
    
    @patch('src.autoscaling.boto3.client')
    def test_scale_in_cooldown_is_three_hundred_seconds(self, mock_boto_client):
        """Test scale-in cooldown is 300 seconds (Requirement 6.5)"""
        endpoint_name = "test-endpoint"
        
        config = AutoScalingConfig(
            endpoint_name=endpoint_name,
            scale_in_cooldown=300
        )
        
        assert config.scale_in_cooldown == 300


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
