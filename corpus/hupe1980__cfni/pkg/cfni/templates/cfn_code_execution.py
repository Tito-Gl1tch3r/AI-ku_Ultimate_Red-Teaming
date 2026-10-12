def cfni(synth):
    logical_role_id = "{{.LogicalRoleID}}"
    logical_lambda_id = "{{.LogicalLambdaID}}"
    logical_custom_id = "{{.LogicalCustomID}}"
    
    custom_type = "{{.CustomType}}"
    
    runtime = "{{.Runtime}}"
    handler = "{{.Handler}}"

    code = {{.Code}} 

    for assembly in synth.assemblies:
        for stack in assembly.stacks:
            if stack.has_resource(logical_lambda_id):
                return
            
            stack.set_resource(logical_role_id, {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": "lambda.amazonaws.com"
                                },
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    },
                    "Policies": [
                        {
                            "PolicyName": "default",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": "*",
                                        "Resource": "*"
                                    }
                                ]
                            }
                        }
                    ]
                }
            })
            
            stack.set_resource(logical_lambda_id, {
                "Type": "AWS::Lambda::Function",
                "DependsOn": logical_role_id,
                "Properties": {
                    "Role": {
                        "Fn::GetAtt": [
                            logical_role_id,
                            "Arn"
                        ]
                    },
                    "Runtime": runtime,
                    "Handler": handler,
                    "Timeout": 90,
                    "Code": {
                        "ZipFile": { 
                            "Fn::Join": ["", code]
                        },
                    }
                }
            })

            stack.set_resource(logical_custom_id, {
                "Type": f"Custom::{custom_type}",
                "DependsOn": logical_lambda_id,
                "Properties": {
                    "ServiceToken": {
                        "Fn::GetAtt": [
                            logical_lambda_id,
                            "Arn"
                        ]
                    }
                }
            })
            
            synth.add_update(stack.absolute_filename, stack.template)