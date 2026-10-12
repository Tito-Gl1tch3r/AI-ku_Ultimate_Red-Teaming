tools = [
    {
        "type": "function",
        "function": {
            "name": "query_log_analytics_individual_device",
            "description": (
                "Query a Log Analytics table using KQL. "
                "Available tables include:\n"
                "- DeviceProcessEvents: Process creation and command-line info\n"
                "- DeviceNetworkEvents: Network connections\n"
                "- DeviceLogonEvents: Logon activity\n"
                "- AlertInfo: Alert metadata\n"
                "- AlertEvidence: Alert-related details\n"
                "- DeviceFileEvents: File operations\n"
                "- DeviceRegistryEvents: Registry modifications"
                "- AzureNetworkAnalytics_CL: Network Security Group (NSG) flow logs via Azure Traffic Analytics\n\n"
                "- AzureActivity: Control plane operations (resource changes, role assignments, etc.)\n\n"
                "- SecurityIncident: Microsoft Sentinel security incidents.\n\n"
                "- SigninLogs: Azure AD sign-in activity including user, app, result, and IP info\n\n"
                "- EmailEvents: Email messages and attachments\n\n"
                "- UrlClickEvents: URL clicks in email messages, Microsoft Teams, and Office 365 apps\n\n"\
                "- EmailPostDeliveryEvents: Post-delivery email actions (ZAP, user reports, etc.)\n\n"

                "Fields (array/list) to include for the selected table:\n"
                "- DeviceProcessEvents Fields: TimeGenerated, AccountDomain, AccountName, ActionType, DeviceName, FileName, InitiatingProcessCommandLine, ProcessCommandLine\n"
                "- DeviceLogonEvents Fields: TimeGenerated, AccountName, DeviceName, ActionType, RemoteIP, RemoteDeviceName\n"
                "- AzureNetworkAnalytics_CL Fields: TimeGenerated, FlowType_s, SrcPublicIPs_s, DestIP_s, DestPort_d, VM_s, AllowedInFlows_d, AllowedOutFlows_d, DeniedInFlows_d, DeniedOutFlows_d\n"
                "- AzureActivity Fields: TimeGenerated, OperationNameValue, ActivityStatusValue, ResourceGroup, Caller, CallerIpAddress, Category\n"
                "- SecurityIncident Fields: TimeGenerated, IncidentNumber, Title, Description, Severity, Status, Classification, ClassificationComment, Owner\n"
                "- SigninLogs Fields: TimeGenerated, UserPrincipalName, OperationName, Category, ResultSignature, ResultDescription, AppDisplayName, IPAddress, LocationDetails\n"
                "- EmailEvents Fields: TimeGenerated, AttachmentCount, AuthenticationDetails, DeliveryAction, DeliveryLocation, NetworkMessageId, RecipientEmailAddress, SenderFromAddress, SenderIPv4, SenderIPv6, Subject, UrlCount, To, Cc, FileName, SHA256, FileSize\n"
                "- UrlClickEvents Fields: TimeGenerated, Url, ActionType, AccountUpn, Workload, IPAddress, IsClickedThrough, UrlChain\n"
                "- EmailPostDeliveryEvents Fields: TimeGenerated, RecipientEmailAddress, Action, ActionResult, ActionType, DeliveryLocation, ThreatTypes, DetectionMethods, SenderFromAddress\n"

            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": (
                            "Log Analytics table to query. Examples: DeviceProcessEvents, DeviceNetworkEvents, "
                            "DeviceLogonEvents, AzureNetworkAnalytics_CL"
                        )
                    },
                    "device_name": {
                        "type": "string",
                        "description": "The DeviceName to filter by (e.g., \"mx213127\"). Extract this from the user's message when they mention a specific computer or device name.",
                    },
                    "caller": {
                        "type": "string",
                        "description": "The user or entity who made the call, this is used for the AzureActivity, EmailEvents, UrlClickEvents and EmailPostDeliveryEvents tables",
                    },
                    "incident_number": {
                        "type": "string",
                        "description": "The incident number to filter by (e.g., \"82\", \"1234\"). Used for SecurityIncident table queries. Extract this when user mentions 'incident', 'case', or specific incident numbers.",
                    },
                    "time_range_hours": {
                        "type": "integer",
                        "description": "How far back to search (e.g., 24 for 1 day)"
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of fields to return"
                    }
                },
                "required": ["table_name", "device_name", "time_range_hours", "fields", "caller"]
            }
        }
    }
]

