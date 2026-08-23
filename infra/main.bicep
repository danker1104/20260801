targetScope = 'resourceGroup'

@description('Primary deployment location')
param location string = resourceGroup().location

@description('Container Apps environment name')
param containerAppsEnvironmentName string = 'cae-${uniqueString(resourceGroup().id)}'

@description('Container App name')
param containerAppName string = 'ca-backend-${uniqueString(resourceGroup().id)}'

@description('Frontend Container App name')
param frontendContainerAppName string = 'ca-frontend-${uniqueString(resourceGroup().id)}'

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string = 'log-${uniqueString(resourceGroup().id)}'

@secure()
@description('Bearer token signing key for backend auth (32+ chars)')
param authSecret string = ''

@secure()
@description('Kakao Maps API key')
param kakaoMapsApiKey string = ''

@secure()
@description('Gemini API key')
param geminiApiKey string = ''

@description('Container Registry name')
param containerRegistryName string = 'cr${uniqueString(resourceGroup().id)}'

var hasKakaoMapsApiKey = !empty(kakaoMapsApiKey)
var hasGeminiApiKey = !empty(geminiApiKey)
var effectiveAuthSecret = empty(authSecret)
  ? guid(resourceGroup().id, containerAppName, 'auth-secret-fallback')
  : authSecret

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      searchVersion: 1
      legacy: 0
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {}
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
  }
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: {
    'azd-service-name': 'backend'
  }
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'Auto'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: concat(
        [
          {
            name: 'registry-password'
            value: containerRegistry.listCredentials().passwords[0].value
          }
          {
            name: 'auth-secret'
            value: effectiveAuthSecret
          }
        ],
        hasKakaoMapsApiKey
          ? [
              {
                name: 'kakao-maps-api-key'
                value: kakaoMapsApiKey
              }
            ]
          : [],
        hasGeminiApiKey
          ? [
              {
                name: 'gemini-api-key'
                value: geminiApiKey
              }
            ]
          : []
      )
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: concat(
            [
              {
                name: 'PORT'
                value: '8000'
              }
              {
                name: 'FASTAPI_HOST'
                value: '0.0.0.0'
              }
              {
                name: 'FASTAPI_PORT'
                value: '8000'
              }
              {
                name: 'DEBUG'
                value: 'false'
              }
              {
                name: 'AUTH_SECRET'
                secretRef: 'auth-secret'
              }
            ],
            hasKakaoMapsApiKey
              ? [
                  {
                    name: 'KAKAO_MAPS_API_KEY'
                    secretRef: 'kakao-maps-api-key'
                  }
                ]
              : [],
            hasGeminiApiKey
              ? [
                  {
                    name: 'GEMINI_API_KEY'
                    secretRef: 'gemini-api-key'
                  }
                ]
              : []
          )
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 12
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 30
              periodSeconds: 15
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendContainerAppName
  location: location
  tags: {
    'azd-service-name': 'frontend'
  }
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'Auto'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
            {
              name: 'BACKEND_ORIGIN'
              value: 'https://${backendApp.properties.configuration.ingress.fqdn}'
            }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 80
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 80
              }
              initialDelaySeconds: 15
              periodSeconds: 15
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

output AZURE_CONTAINER_APP_NAME string = backendApp.name
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = managedEnvironment.name
output BACKEND_URL string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output FRONTEND_URL string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.name
