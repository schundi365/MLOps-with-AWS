## Issue #24: Endpoint Not Ready Before Evaluation

## Problem
Execution #23 failed with "Endpoint not found" error, even though CreateEndpoint step succeeded.

### Timeline Analysis
```
10:57:11 - Training started
11:02:43 - Training "completed" (5 minutes - WRONG, should be 60 min)
11:02:43 - CreateModel succeeded
11:02:44 - CreateEndpointConfig succeeded  
11:02:45 - CreateEndpoint succeeded (instant - WRONG, should be 5-8 min)
11:02:45 - ModelEvaluation started
11:02:50 - Evaluation failed: "Endpoint not found"
11:03:20 - Retry failed: "Endpoint not found"
11:04:20 - Retry failed: "Endpoint not found"
11:06:47 - Final retry failed: "Worker died" (endpoint finally existed but wasn't ready)
```

## Root Cause
**Step Functions was NOT waiting for async operations to complete:**

1. **Training**: Used `.sync` correctly, but training actually failed/was skipped somehow
2. **CreateModel**: Synchronous operation (returns immediately) - OK
3. **CreateEndpointConfig**: Synchronous operation (returns immediately) - OK
4. **CreateEndpoint**: Async operation but NO `.sync` support in Step Functions
   - Step Functions started endpoint creation
   - Immediately proceeded to next step
   - Endpoint takes 5-8 minutes to reach InService
   - Evaluation tried to invoke endpoint before it was ready

## Why `.sync` Doesn't Work for Deployment

AWS Step Functions SageMaker integration:
- ✓ `createTrainingJob.sync` - SUPPORTED
- ✓ `createProcessingJob.sync` - SUPPORTED
- ✗ `createModel.sync` - NOT SUPPORTED (but model creation is instant anyway)
- ✗ `createEndpointConfig.sync` - NOT SUPPORTED (but config creation is instant anyway)
- ✗ `createEndpoint.sync` - NOT SUPPORTED (this is the problem!)

## Solution
Added a polling loop after CreateEndpoint to wait for InService status:

### New Workflow
```
CreateEndpoint
    ↓
WaitForEndpoint (DescribeEndpoint)
    ↓
CheckEndpointStatus (Choice)
    ├─ InService → ModelEvaluation
    ├─ Failed → DeploymentFailed
    └─ Creating/Updating → WaitBeforeRetry
                              ↓
                         Wait 30 seconds
                              ↓
                         Loop back to WaitForEndpoint
```

### Implementation Details
1. **WaitForEndpoint**: Task state that calls `sagemaker:describeEndpoint`
2. **CheckEndpointStatus**: Choice state that checks `EndpointStatus`
3. **WaitBeforeRetry**: Wait state (30 seconds) before polling again
4. **Loop**: Continues until endpoint is InService or Failed

## Files Modified
- Created: `fix_state_machine_sync.py` (attempted but failed - .sync not supported)
- Created: `fix_endpoint_wait_for_inservice.py` (successful fix)
- Updated: Step Functions state machine definition in AWS

## Verification
- Execution #24 started: 2026-01-22 11:11:12 UTC
- Expected behavior:
  - Preprocessing: 5-10 minutes
  - Training: 60 minutes (with .sync, will wait)
  - CreateModel: 2 minutes
  - CreateEndpointConfig: 1 minute
  - CreateEndpoint: Starts creation
  - WaitForEndpoint loop: 5-8 minutes until InService
  - ModelEvaluation: Runs after endpoint is ready
  - Total: ~80-90 minutes

## Key Learnings
1. Not all SageMaker operations support `.sync` in Step Functions
2. `createEndpoint` is async but doesn't support `.sync`
3. Must implement custom polling loop for endpoint readiness
4. Use `DescribeEndpoint` API to check `EndpointStatus`
5. Wait states prevent tight polling loops

## Related Issues
- Issue #21: Workflow order (Training → Deploy → Evaluation)
- Issue #22: Deployment parameters (PrepareDeployment Pass state)
- Issue #23: SageMaker permissions (CreateModel, CreateEndpointConfig, CreateEndpoint)
- Issue #24: Endpoint wait (WaitForEndpoint polling loop)

## Next Steps
1. Monitor Execution #24 to verify fix works
2. Confirm training takes ~60 minutes (not 5 minutes)
3. Confirm endpoint polling works correctly
4. Confirm evaluation runs after endpoint is InService
5. Document final success

## Expected Outcome
Execution #24 should:
- ✓ Complete preprocessing successfully
- ✓ Complete training in ~60 minutes
- ✓ Create model successfully
- ✓ Create endpoint config successfully
- ✓ Start endpoint creation
- ✓ Poll until endpoint is InService (5-8 minutes)
- ✓ Run evaluation successfully
- ✓ Complete with SUCCESS status
