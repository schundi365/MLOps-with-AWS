"""
Unit tests for CloudWatch monitoring setup.

Tests cover:
- Dashboard creation
- Alarm configuration

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
"""

import json
import pytest

from src.monitoring import (
    create_dashboard_configuration,
    create_high_error_rate_alarm,
    create_high_latency_alarm,
    create_monitoring_setup
)


class TestDashboardCreation:
    """Test CloudWatch dashboard creation"""
    
    def test_create_dashboard_with_default_name(self):
        """Test dashboard creation with default dashboard name"""
        endpoint_name = "test-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        
        # Verify dashboard name
        assert config['DashboardName'] == f"{endpoint_name}-dashboard"
        
        # Verify dashboard body is valid JSON
        dashboard_body = json.loads(config['DashboardBody'])
        assert 'widgets' in dashboard_body
        assert isinstance(dashboard_body['widgets'], list)
    
    def test_create_dashboard_with_custom_name(self):
        """Test dashboard creation with custom dashboard name"""
        endpoint_name = "test-endpoint"
        custom_name = "my-custom-dashboard"
        
        config = create_dashboard_configuration(
            endpoint_name=endpoint_name,
            dashboard_name=custom_name
        )
        
        # Verify custom dashboard name is used
        assert config['DashboardName'] == custom_name
    
    def test_create_dashboard_with_custom_region(self):
        """Test dashboard creation with custom AWS region"""
        endpoint_name = "test-endpoint"
        region = "us-west-2"
        
        config = create_dashboard_configuration(
            endpoint_name=endpoint_name,
            region=region
        )
        
        # Verify region is set in all widgets
        dashboard_body = json.loads(config['DashboardBody'])
        for widget in dashboard_body['widgets']:
            assert widget['properties']['region'] == region
    
    def test_dashboard_contains_invocations_widget(self):
        """Test dashboard contains invocations per minute widget (Requirement 7.1)"""
        endpoint_name = "test-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        dashboard_body = json.loads(config['DashboardBody'])
        
        # Find invocations widget
        invocations_widget = None
        for widget in dashboard_body['widgets']:
            if widget['properties']['title'] == "Invocations per Minute":
                invocations_widget = widget
                break
        
        assert invocations_widget is not None
        
        # Verify widget properties
        metrics = invocations_widget['properties']['metrics']
        assert len(metrics) > 0
        assert metrics[0][0] == "AWS/SageMaker"
        assert metrics[0][1] == "Invocations"
        assert metrics[0][2] == "EndpointName"
        assert metrics[0][3] == endpoint_name
        
        # Verify period is 60 seconds (1 minute)
        assert invocations_widget['properties']['period'] == 60
    
    def test_dashboard_contains_latency_widget(self):
        """Test dashboard contains model latency widget with P50, P90, P99 (Requirement 7.2)"""
        endpoint_name = "test-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        dashboard_body = json.loads(config['DashboardBody'])
        
        # Find latency widget
        latency_widget = None
        for widget in dashboard_body['widgets']:
            if "Latency" in widget['properties']['title']:
                latency_widget = widget
                break
        
        assert latency_widget is not None
        assert "P50, P90, P99" in latency_widget['properties']['title']
        
        # Verify all three percentiles are present
        metrics = latency_widget['properties']['metrics']
        assert len(metrics) >= 3
        
        # Check for P50, P90, P99 statistics
        stats = []
        for metric in metrics:
            if isinstance(metric[-1], dict) and 'stat' in metric[-1]:
                stats.append(metric[-1]['stat'])
        
        assert 'p50' in stats
        assert 'p90' in stats
        assert 'p99' in stats
    
    def test_dashboard_contains_error_rates_widget(self):
        """Test dashboard contains error rates widget for 4xx and 5xx (Requirement 7.3)"""
        endpoint_name = "test-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        dashboard_body = json.loads(config['DashboardBody'])
        
        # Find error rates widget
        error_widget = None
        for widget in dashboard_body['widgets']:
            if "Error" in widget['properties']['title']:
                error_widget = widget
                break
        
        assert error_widget is not None
        assert "4xx and 5xx" in error_widget['properties']['title']
        
        # Verify both 4xx and 5xx metrics are present
        metrics = error_widget['properties']['metrics']
        metric_names = [m[1] for m in metrics]
        
        assert "Invocation4XXErrors" in metric_names
        assert "Invocation5XXErrors" in metric_names
    
    def test_dashboard_contains_cpu_utilization_widget(self):
        """Test dashboard contains CPU utilization widget (Requirement 7.4)"""
        endpoint_name = "test-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        dashboard_body = json.loads(config['DashboardBody'])
        
        # Find CPU utilization widget
        cpu_widget = None
        for widget in dashboard_body['widgets']:
            if "CPU" in widget['properties']['title']:
                cpu_widget = widget
                break
        
        assert cpu_widget is not None
        
        # Verify metric
        metrics = cpu_widget['properties']['metrics']
        assert len(metrics) > 0
        assert metrics[0][1] == "CPUUtilization"
        
        # Verify Y-axis is configured for percentage (0-100)
        y_axis = cpu_widget['properties']['yAxis']['left']
        assert y_axis['label'] == "Percent"
        assert y_axis['min'] == 0
        assert y_axis['max'] == 100
    
    def test_dashboard_contains_memory_utilization_widget(self):
        """Test dashboard contains memory utilization widget (Requirement 7.4)"""
        endpoint_name = "test-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        dashboard_body = json.loads(config['DashboardBody'])
        
        # Find memory utilization widget
        memory_widget = None
        for widget in dashboard_body['widgets']:
            if "Memory" in widget['properties']['title']:
                memory_widget = widget
                break
        
        assert memory_widget is not None
        
        # Verify metric
        metrics = memory_widget['properties']['metrics']
        assert len(metrics) > 0
        assert metrics[0][1] == "MemoryUtilization"
        
        # Verify Y-axis is configured for percentage (0-100)
        y_axis = memory_widget['properties']['yAxis']['left']
        assert y_axis['label'] == "Percent"
        assert y_axis['min'] == 0
        assert y_axis['max'] == 100
    
    def test_dashboard_has_all_required_widgets(self):
        """Test dashboard contains all 5 required widgets (Requirement 7.7)"""
        endpoint_name = "test-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        dashboard_body = json.loads(config['DashboardBody'])
        
        # Verify we have exactly 5 widgets
        assert len(dashboard_body['widgets']) == 5
        
        # Verify all widget titles are present
        titles = [w['properties']['title'] for w in dashboard_body['widgets']]
        
        assert "Invocations per Minute" in titles
        assert any("Latency" in t for t in titles)
        assert any("Error" in t for t in titles)
        assert "CPU Utilization" in titles
        assert "Memory Utilization" in titles
    
    def test_dashboard_widgets_have_correct_endpoint_name(self):
        """Test all dashboard widgets reference the correct endpoint name"""
        endpoint_name = "my-ml-endpoint"
        
        config = create_dashboard_configuration(endpoint_name)
        dashboard_body = json.loads(config['DashboardBody'])
        
        # Check each widget references the correct endpoint
        for widget in dashboard_body['widgets']:
            metrics = widget['properties']['metrics']
            for metric in metrics:
                if isinstance(metric, list) and len(metric) > 3:
                    # Check if this metric has endpoint dimension
                    if metric[2] == "EndpointName":
                        assert metric[3] == endpoint_name


class TestHighErrorRateAlarm:
    """Test high error rate alarm configuration"""
    
    def test_create_error_alarm_with_default_name(self):
        """Test error alarm creation with default alarm name"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify alarm name
        assert config['AlarmName'] == f"{endpoint_name}-high-error-rate"
    
    def test_create_error_alarm_with_custom_name(self):
        """Test error alarm creation with custom alarm name"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        custom_name = "my-custom-alarm"
        
        config = create_high_error_rate_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            alarm_name=custom_name
        )
        
        # Verify custom alarm name is used
        assert config['AlarmName'] == custom_name
    
    def test_error_alarm_default_threshold(self):
        """Test error alarm uses default 5% threshold (Requirement 7.5)"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify default threshold is 5.0
        assert config['Threshold'] == 5.0
    
    def test_error_alarm_custom_threshold(self):
        """Test error alarm with custom threshold"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        custom_threshold = 10.0
        
        config = create_high_error_rate_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            threshold=custom_threshold
        )
        
        # Verify custom threshold is used
        assert config['Threshold'] == custom_threshold
    
    def test_error_alarm_sns_action(self):
        """Test error alarm is configured with SNS notification (Requirement 7.5)"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify SNS action is configured
        assert config['ActionsEnabled'] is True
        assert sns_topic_arn in config['AlarmActions']
    
    def test_error_alarm_uses_metric_math(self):
        """Test error alarm uses metric math to calculate error rate percentage"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify Metrics field exists (for metric math)
        assert 'Metrics' in config
        assert isinstance(config['Metrics'], list)
        assert len(config['Metrics']) == 4  # invocations, errors_4xx, errors_5xx, error_rate
        
        # Verify metric IDs
        metric_ids = [m['Id'] for m in config['Metrics']]
        assert 'invocations' in metric_ids
        assert 'errors_4xx' in metric_ids
        assert 'errors_5xx' in metric_ids
        assert 'error_rate' in metric_ids
        
        # Verify error_rate expression
        error_rate_metric = next(m for m in config['Metrics'] if m['Id'] == 'error_rate')
        assert 'Expression' in error_rate_metric
        assert '(errors_4xx + errors_5xx) / invocations * 100' == error_rate_metric['Expression']
        assert error_rate_metric['ReturnData'] is True
    
    def test_error_alarm_evaluation_periods(self):
        """Test error alarm evaluation periods configuration"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify default evaluation periods
        assert config['EvaluationPeriods'] == 2
        assert config['DatapointsToAlarm'] == 2
    
    def test_error_alarm_custom_evaluation_periods(self):
        """Test error alarm with custom evaluation periods"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            evaluation_periods=3,
            datapoints_to_alarm=2
        )
        
        # Verify custom evaluation periods
        assert config['EvaluationPeriods'] == 3
        assert config['DatapointsToAlarm'] == 2
    
    def test_error_alarm_comparison_operator(self):
        """Test error alarm uses GreaterThanThreshold comparison"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify comparison operator
        assert config['ComparisonOperator'] == 'GreaterThanThreshold'
    
    def test_error_alarm_missing_data_treatment(self):
        """Test error alarm treats missing data as not breaching"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify missing data treatment
        assert config['TreatMissingData'] == 'notBreaching'
    
    def test_error_alarm_period(self):
        """Test error alarm uses 5-minute period"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_error_rate_alarm(endpoint_name, sns_topic_arn)
        
        # Verify period is 300 seconds (5 minutes)
        assert config['Period'] == 300


class TestHighLatencyAlarm:
    """Test high latency alarm configuration"""
    
    def test_create_latency_alarm_with_default_name(self):
        """Test latency alarm creation with default alarm name"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify alarm name
        assert config['AlarmName'] == f"{endpoint_name}-high-latency"
    
    def test_create_latency_alarm_with_custom_name(self):
        """Test latency alarm creation with custom alarm name"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        custom_name = "my-latency-alarm"
        
        config = create_high_latency_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            alarm_name=custom_name
        )
        
        # Verify custom alarm name is used
        assert config['AlarmName'] == custom_name
    
    def test_latency_alarm_default_threshold(self):
        """Test latency alarm uses default 1000ms threshold (Requirement 7.6)"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify default threshold is 1000.0 ms
        assert config['Threshold'] == 1000.0
    
    def test_latency_alarm_custom_threshold(self):
        """Test latency alarm with custom threshold"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        custom_threshold = 500.0
        
        config = create_high_latency_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            threshold=custom_threshold
        )
        
        # Verify custom threshold is used
        assert config['Threshold'] == custom_threshold
    
    def test_latency_alarm_sns_action(self):
        """Test latency alarm is configured with SNS notification (Requirement 7.6)"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify SNS action is configured
        assert config['ActionsEnabled'] is True
        assert sns_topic_arn in config['AlarmActions']
    
    def test_latency_alarm_monitors_p99(self):
        """Test latency alarm monitors P99 latency (Requirement 7.6)"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify metric and statistic
        assert config['MetricName'] == 'ModelLatency'
        assert config['Namespace'] == 'AWS/SageMaker'
        assert config['Statistic'] == 'p99'
    
    def test_latency_alarm_dimensions(self):
        """Test latency alarm has correct dimensions"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify dimensions
        dimensions = config['Dimensions']
        assert len(dimensions) == 2
        
        endpoint_dim = next(d for d in dimensions if d['Name'] == 'EndpointName')
        assert endpoint_dim['Value'] == endpoint_name
        
        variant_dim = next(d for d in dimensions if d['Name'] == 'VariantName')
        assert variant_dim['Value'] == 'AllTraffic'
    
    def test_latency_alarm_evaluation_periods(self):
        """Test latency alarm evaluation periods configuration"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify default evaluation periods
        assert config['EvaluationPeriods'] == 2
        assert config['DatapointsToAlarm'] == 2
    
    def test_latency_alarm_custom_evaluation_periods(self):
        """Test latency alarm with custom evaluation periods"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            evaluation_periods=3,
            datapoints_to_alarm=2
        )
        
        # Verify custom evaluation periods
        assert config['EvaluationPeriods'] == 3
        assert config['DatapointsToAlarm'] == 2
    
    def test_latency_alarm_comparison_operator(self):
        """Test latency alarm uses GreaterThanThreshold comparison"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify comparison operator
        assert config['ComparisonOperator'] == 'GreaterThanThreshold'
    
    def test_latency_alarm_missing_data_treatment(self):
        """Test latency alarm treats missing data as not breaching"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify missing data treatment
        assert config['TreatMissingData'] == 'notBreaching'
    
    def test_latency_alarm_period(self):
        """Test latency alarm uses 5-minute period"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        config = create_high_latency_alarm(endpoint_name, sns_topic_arn)
        
        # Verify period is 300 seconds (5 minutes)
        assert config['Period'] == 300


class TestCompleteMonitoringSetup:
    """Test complete monitoring setup with dashboard and alarms"""
    
    def test_create_monitoring_setup_returns_all_components(self):
        """Test complete monitoring setup returns dashboard and both alarms"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        setup = create_monitoring_setup(endpoint_name, sns_topic_arn)
        
        # Verify structure
        assert 'dashboard' in setup
        assert 'alarms' in setup
        assert 'high_error_rate' in setup['alarms']
        assert 'high_latency' in setup['alarms']
    
    def test_monitoring_setup_dashboard_configuration(self):
        """Test monitoring setup creates valid dashboard configuration"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        setup = create_monitoring_setup(endpoint_name, sns_topic_arn)
        
        # Verify dashboard
        dashboard = setup['dashboard']
        assert 'DashboardName' in dashboard
        assert 'DashboardBody' in dashboard
        assert dashboard['DashboardName'] == f"{endpoint_name}-dashboard"
    
    def test_monitoring_setup_error_alarm_configuration(self):
        """Test monitoring setup creates valid error rate alarm"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        setup = create_monitoring_setup(endpoint_name, sns_topic_arn)
        
        # Verify error alarm
        error_alarm = setup['alarms']['high_error_rate']
        assert error_alarm['AlarmName'] == f"{endpoint_name}-high-error-rate"
        assert error_alarm['Threshold'] == 5.0
        assert sns_topic_arn in error_alarm['AlarmActions']
    
    def test_monitoring_setup_latency_alarm_configuration(self):
        """Test monitoring setup creates valid latency alarm"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        setup = create_monitoring_setup(endpoint_name, sns_topic_arn)
        
        # Verify latency alarm
        latency_alarm = setup['alarms']['high_latency']
        assert latency_alarm['AlarmName'] == f"{endpoint_name}-high-latency"
        assert latency_alarm['Threshold'] == 1000.0
        assert sns_topic_arn in latency_alarm['AlarmActions']
    
    def test_monitoring_setup_with_custom_dashboard_name(self):
        """Test monitoring setup with custom dashboard name"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        custom_dashboard = "my-dashboard"
        
        setup = create_monitoring_setup(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            dashboard_name=custom_dashboard
        )
        
        # Verify custom dashboard name
        assert setup['dashboard']['DashboardName'] == custom_dashboard
    
    def test_monitoring_setup_with_custom_region(self):
        """Test monitoring setup with custom AWS region"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-west-2:123456789012:test-topic"
        region = "us-west-2"
        
        setup = create_monitoring_setup(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            region=region
        )
        
        # Verify region in dashboard
        dashboard_body = json.loads(setup['dashboard']['DashboardBody'])
        for widget in dashboard_body['widgets']:
            assert widget['properties']['region'] == region
    
    def test_monitoring_setup_with_custom_thresholds(self):
        """Test monitoring setup with custom alarm thresholds"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        custom_error_threshold = 10.0
        custom_latency_threshold = 500.0
        
        setup = create_monitoring_setup(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            error_rate_threshold=custom_error_threshold,
            latency_threshold=custom_latency_threshold
        )
        
        # Verify custom thresholds
        assert setup['alarms']['high_error_rate']['Threshold'] == custom_error_threshold
        assert setup['alarms']['high_latency']['Threshold'] == custom_latency_threshold
    
    def test_monitoring_setup_all_components_reference_same_endpoint(self):
        """Test all monitoring components reference the same endpoint"""
        endpoint_name = "production-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        
        setup = create_monitoring_setup(endpoint_name, sns_topic_arn)
        
        # Check dashboard references endpoint
        dashboard_body = json.loads(setup['dashboard']['DashboardBody'])
        for widget in dashboard_body['widgets']:
            metrics = widget['properties']['metrics']
            for metric in metrics:
                if isinstance(metric, list) and len(metric) > 3:
                    if metric[2] == "EndpointName":
                        assert metric[3] == endpoint_name
        
        # Check error alarm references endpoint
        error_alarm = setup['alarms']['high_error_rate']
        for metric in error_alarm['Metrics']:
            if 'MetricStat' in metric:
                dimensions = metric['MetricStat']['Metric']['Dimensions']
                endpoint_dim = next(d for d in dimensions if d['Name'] == 'EndpointName')
                assert endpoint_dim['Value'] == endpoint_name
        
        # Check latency alarm references endpoint
        latency_alarm = setup['alarms']['high_latency']
        dimensions = latency_alarm['Dimensions']
        endpoint_dim = next(d for d in dimensions if d['Name'] == 'EndpointName')
        assert endpoint_dim['Value'] == endpoint_name


class TestAlarmDescriptions:
    """Test alarm descriptions are informative"""
    
    def test_error_alarm_has_descriptive_description(self):
        """Test error alarm has informative description"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        threshold = 5.0
        
        config = create_high_error_rate_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            threshold=threshold
        )
        
        # Verify description contains threshold and endpoint name
        description = config['AlarmDescription']
        assert str(threshold) in description
        assert endpoint_name in description
        assert "error rate" in description.lower()
    
    def test_latency_alarm_has_descriptive_description(self):
        """Test latency alarm has informative description"""
        endpoint_name = "test-endpoint"
        sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        threshold = 1000.0
        
        config = create_high_latency_alarm(
            endpoint_name=endpoint_name,
            sns_topic_arn=sns_topic_arn,
            threshold=threshold
        )
        
        # Verify description contains threshold and endpoint name
        description = config['AlarmDescription']
        assert str(int(threshold)) in description
        assert endpoint_name in description
        assert "latency" in description.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
