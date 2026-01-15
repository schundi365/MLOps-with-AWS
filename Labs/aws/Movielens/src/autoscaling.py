"""
Auto-scaling configuration for SageMaker endpoints.

This module provides functionality to configure auto-scaling policies for
SageMaker inference endpoints based on invocations per instance.
"""

import boto3
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AutoScalingConfig:
    """Configuration for SageMaker endpoint auto-scaling."""
    
    def __init__(
        self,
        endpoint_name: str,
        variant_name: str = "AllTraffic",
        min_capacity: int = 1,
        max_capacity: int = 5,
        target_value: float = 70.0,
        scale_out_cooldown: int = 60,
        scale_in_cooldown: int = 300,
        region_name: Optional[str] = None
    ):
        """
        Initialize auto-scaling configuration.
        
        Args:
            endpoint_name: Name of the SageMaker endpoint
            variant_name: Name of the production variant (default: "AllTraffic")
            min_capacity: Minimum number of instances (default: 1)
            max_capacity: Maximum number of instances (default: 5)
            target_value: Target invocations per instance (default: 70.0)
            scale_out_cooldown: Cooldown period for scale-out in seconds (default: 60)
            scale_in_cooldown: Cooldown period for scale-in in seconds (default: 300)
            region_name: AWS region name (optional)
        """
        self.endpoint_name = endpoint_name
        self.variant_name = variant_name
        self.min_capacity = min_capacity
        self.max_capacity = max_capacity
        self.target_value = target_value
        self.scale_out_cooldown = scale_out_cooldown
        self.scale_in_cooldown = scale_in_cooldown
        
        # Initialize AWS clients
        self.autoscaling_client = boto3.client(
            'application-autoscaling',
            region_name=region_name
        )
        
        # Resource ID for SageMaker endpoint variant
        self.resource_id = f"endpoint/{endpoint_name}/variant/{variant_name}"
        
    def register_scalable_target(self) -> Dict[str, Any]:
        """
        Register the SageMaker endpoint as a scalable target.
        
        Returns:
            Response from register_scalable_target API call
            
        Raises:
            Exception: If registration fails
        """
        try:
            logger.info(
                f"Registering scalable target for endpoint {self.endpoint_name} "
                f"with min={self.min_capacity}, max={self.max_capacity}"
            )
            
            response = self.autoscaling_client.register_scalable_target(
                ServiceNamespace='sagemaker',
                ResourceId=self.resource_id,
                ScalableDimension='sagemaker:variant:DesiredInstanceCount',
                MinCapacity=self.min_capacity,
                MaxCapacity=self.max_capacity
            )
            
            logger.info(f"Successfully registered scalable target: {self.resource_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to register scalable target: {str(e)}")
            raise
    
    def create_scaling_policy(self) -> Dict[str, Any]:
        """
        Create a target tracking scaling policy for the endpoint.
        
        The policy scales based on SageMakerVariantInvocationsPerInstance metric.
        
        Returns:
            Response from put_scaling_policy API call
            
        Raises:
            Exception: If policy creation fails
        """
        try:
            policy_name = f"{self.endpoint_name}-target-tracking-policy"
            
            logger.info(
                f"Creating target tracking scaling policy '{policy_name}' "
                f"with target value={self.target_value}"
            )
            
            response = self.autoscaling_client.put_scaling_policy(
                PolicyName=policy_name,
                ServiceNamespace='sagemaker',
                ResourceId=self.resource_id,
                ScalableDimension='sagemaker:variant:DesiredInstanceCount',
                PolicyType='TargetTrackingScaling',
                TargetTrackingScalingPolicyConfiguration={
                    'TargetValue': self.target_value,
                    'PredefinedMetricSpecification': {
                        'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
                    },
                    'ScaleOutCooldown': self.scale_out_cooldown,
                    'ScaleInCooldown': self.scale_in_cooldown
                }
            )
            
            logger.info(
                f"Successfully created scaling policy. "
                f"Policy ARN: {response.get('PolicyARN', 'N/A')}"
            )
            return response
            
        except Exception as e:
            logger.error(f"Failed to create scaling policy: {str(e)}")
            raise
    
    def configure_autoscaling(self) -> Dict[str, Any]:
        """
        Configure complete auto-scaling setup for the endpoint.
        
        This method registers the scalable target and creates the scaling policy.
        
        Returns:
            Dictionary containing both registration and policy responses
            
        Raises:
            Exception: If configuration fails
        """
        try:
            logger.info(f"Configuring auto-scaling for endpoint {self.endpoint_name}")
            
            # Register scalable target
            registration_response = self.register_scalable_target()
            
            # Create scaling policy
            policy_response = self.create_scaling_policy()
            
            logger.info(
                f"Auto-scaling configuration complete for {self.endpoint_name}"
            )
            
            return {
                'registration': registration_response,
                'policy': policy_response
            }
            
        except Exception as e:
            logger.error(f"Failed to configure auto-scaling: {str(e)}")
            raise
    
    def delete_scaling_policy(self) -> Dict[str, Any]:
        """
        Delete the scaling policy for the endpoint.
        
        Returns:
            Response from delete_scaling_policy API call
            
        Raises:
            Exception: If deletion fails
        """
        try:
            policy_name = f"{self.endpoint_name}-target-tracking-policy"
            
            logger.info(f"Deleting scaling policy '{policy_name}'")
            
            response = self.autoscaling_client.delete_scaling_policy(
                PolicyName=policy_name,
                ServiceNamespace='sagemaker',
                ResourceId=self.resource_id,
                ScalableDimension='sagemaker:variant:DesiredInstanceCount'
            )
            
            logger.info(f"Successfully deleted scaling policy")
            return response
            
        except Exception as e:
            logger.error(f"Failed to delete scaling policy: {str(e)}")
            raise
    
    def deregister_scalable_target(self) -> Dict[str, Any]:
        """
        Deregister the scalable target.
        
        Returns:
            Response from deregister_scalable_target API call
            
        Raises:
            Exception: If deregistration fails
        """
        try:
            logger.info(f"Deregistering scalable target {self.resource_id}")
            
            response = self.autoscaling_client.deregister_scalable_target(
                ServiceNamespace='sagemaker',
                ResourceId=self.resource_id,
                ScalableDimension='sagemaker:variant:DesiredInstanceCount'
            )
            
            logger.info(f"Successfully deregistered scalable target")
            return response
            
        except Exception as e:
            logger.error(f"Failed to deregister scalable target: {str(e)}")
            raise
    
    def get_scaling_policy(self) -> Dict[str, Any]:
        """
        Get the current scaling policy configuration.
        
        Returns:
            Response from describe_scaling_policies API call
            
        Raises:
            Exception: If retrieval fails
        """
        try:
            policy_name = f"{self.endpoint_name}-target-tracking-policy"
            
            response = self.autoscaling_client.describe_scaling_policies(
                PolicyNames=[policy_name],
                ServiceNamespace='sagemaker',
                ResourceId=self.resource_id,
                ScalableDimension='sagemaker:variant:DesiredInstanceCount'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get scaling policy: {str(e)}")
            raise


def configure_endpoint_autoscaling(
    endpoint_name: str,
    variant_name: str = "AllTraffic",
    min_capacity: int = 1,
    max_capacity: int = 5,
    target_value: float = 70.0,
    scale_out_cooldown: int = 60,
    scale_in_cooldown: int = 300,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Configure auto-scaling for a SageMaker endpoint.
    
    This is a convenience function that creates an AutoScalingConfig instance
    and configures auto-scaling in one call.
    
    Args:
        endpoint_name: Name of the SageMaker endpoint
        variant_name: Name of the production variant (default: "AllTraffic")
        min_capacity: Minimum number of instances (default: 1)
        max_capacity: Maximum number of instances (default: 5)
        target_value: Target invocations per instance (default: 70.0)
        scale_out_cooldown: Cooldown period for scale-out in seconds (default: 60)
        scale_in_cooldown: Cooldown period for scale-in in seconds (default: 300)
        region_name: AWS region name (optional)
        
    Returns:
        Dictionary containing registration and policy responses
        
    Raises:
        Exception: If configuration fails
        
    Example:
        >>> result = configure_endpoint_autoscaling(
        ...     endpoint_name="movielens-endpoint",
        ...     min_capacity=1,
        ...     max_capacity=5,
        ...     target_value=70.0
        ... )
    """
    config = AutoScalingConfig(
        endpoint_name=endpoint_name,
        variant_name=variant_name,
        min_capacity=min_capacity,
        max_capacity=max_capacity,
        target_value=target_value,
        scale_out_cooldown=scale_out_cooldown,
        scale_in_cooldown=scale_in_cooldown,
        region_name=region_name
    )
    
    return config.configure_autoscaling()
