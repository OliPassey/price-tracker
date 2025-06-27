# Azure DevOps Pipeline Setup Guide

This guide will help you set up the Azure DevOps pipeline to automatically build and push your Price Tracker Docker images to your registry at `dock.ptslondon.co.uk`.

## Prerequisites

1. Azure DevOps project
2. GitHub repository with your Price Tracker code
3. Access to your Docker registry at `dock.ptslondon.co.uk`
4. Admin permissions in Azure DevOps to create service connections

## Step 1: Create GitHub Service Connection

1. In your Azure DevOps project, go to **Project Settings** (bottom left)
2. Under **Pipelines**, click **Service connections**
3. Click **New service connection**
4. Select **GitHub** and click **Next**
5. Choose **Azure Pipelines** app:
   - Click **Authorize using OAuth**
   - Sign in to GitHub and authorize Azure Pipelines
   - OR use **Personal Access Token** if you prefer:
     - Create a GitHub PAT with `repo` scope
     - Enter your GitHub username and PAT
6. **Service connection name**: `github` (this must match the pipeline)
7. Check **Grant access permission to all pipelines**
8. Click **Save**

## Step 2: Create Docker Registry Service Connection

1. In **Service connections**, click **New service connection**
2. Select **Docker Registry** and click **Next**
3. Choose **Others** for registry type
4. Fill in the details:
   - **Docker Registry**: `https://dock.ptslondon.co.uk`
   - **Docker ID**: Your registry username
   - **Docker Password**: Your registry password
   - **Service connection name**: `dock-ptslondon-connection`
5. Check **Grant access permission to all pipelines**
6. Click **Save**

## Step 3: Update Pipeline Configuration

1. Open `azure-pipelines.yml` in your repository
2. Update the GitHub repository path in the resources section:
   ```yaml
   resources:
     repositories:
     - repository: self
       type: github
       endpoint: github  # This matches your GitHub service connection
       name: your-github-username/price-tracker  # Replace with your actual repo
   ```

## Step 4: Create the Pipeline

1. In Azure DevOps, go to **Pipelines** → **Pipelines**
2. Click **New pipeline**
3. Select **GitHub**
4. Select your Price Tracker repository from GitHub
5. Azure DevOps will detect the `azure-pipelines.yml` file
6. Review the pipeline and click **Run**

## Alternative: Manual YAML Pipeline Setup

If you prefer to create the pipeline manually:
1. Go to **Pipelines** → **Pipelines**
2. Click **New pipeline**
3. Select **GitHub YAML**
4. Select your repository
5. Choose **Existing Azure Pipelines YAML file**
6. Select `/azure-pipelines.yml`
7. Click **Continue**
8. Review the pipeline and click **Run**

## Step 4: Configure Environments (Advanced Pipeline Only)

If using the advanced pipeline, create environments:

1. Go to **Pipelines** → **Environments**
2. Click **New environment**
3. Create two environments:
   - **Name**: `price-tracker-dev`
   - **Name**: `price-tracker-prod`
4. For each environment, you can add approval gates:
   - Go to the environment
   - Click the three dots → **Approvals and checks**
   - Add **Approvals** for production

## Step 5: GitHub Integration Benefits

Using GitHub as your source provides several advantages:

### Automatic Sync
- Changes to your GitHub repository automatically trigger Azure DevOps pipelines
- No need to maintain separate Azure Repos
- Keeps your source code in one place

### Branch Protection
- Configure branch protection rules in GitHub
- Require pull request reviews
- Status checks from Azure DevOps can block merges

### GitHub Actions Alternative
While Azure DevOps pulls from GitHub, you could also:
- Use GitHub Actions for CI/CD (free tier: 2000 minutes/month)
- Mirror from GitHub to Azure DevOps for backup
- Use hybrid approach (GitHub Actions + Azure DevOps)

## Step 6: Pipeline Configuration

The pipeline is configured to:

### Triggers
- **Push to main**: Builds and deploys to production
- **Push to develop**: Builds and deploys to development
- **Pull requests**: Builds and tests only

### Build Process
1. Checkout source code
2. Build Docker image
3. Run container tests
4. Push to registry (if not PR)
5. Security scan (optional)
6. Deploy to appropriate environment

### Variables Used
- `dockerRegistryServiceConnection`: Service connection name
- `imageRepository`: `price-tracker`
- `containerRegistry`: `dock.ptslondon.co.uk`
- `tag`: Uses build ID for versioning

## Step 7: Customize for Your Needs

### Registry Settings
If your registry requires different settings, update these variables in the pipeline:

```yaml
variables:
  dockerRegistryServiceConnection: 'your-connection-name'
  imageRepository: 'your-repo-name'
  containerRegistry: 'dock.ptslondon.co.uk'
```

### Branch Strategy
Current setup:
- `main` branch → Production deployment
- `develop` branch → Development deployment

To change this, modify the trigger and condition sections.

### Security Scanning
The advanced pipeline includes Trivy security scanning. To disable:
- Remove the `SecurityScan` stage
- Remove it from the `dependsOn` lists

## Step 8: Verify the Setup

1. Make a small change to your code
2. Push to the `develop` branch (for testing)
3. Watch the pipeline run in Azure DevOps
4. Verify the image appears in your registry
5. Check that the application deploys correctly

## Troubleshooting

### Common Issues

1. **GitHub Service Connection Failed**
   - Verify GitHub permissions for Azure Pipelines app
   - Check that the repository path is correct
   - Ensure the service connection name matches (`github`)
   - Try re-authorizing the GitHub connection

2. **Service Connection Failed**
   - Verify registry credentials
   - Check registry URL format
   - Ensure registry is accessible from Azure

2. **Docker Service Connection Failed**
   - Check Dockerfile syntax
   - Verify all required files are in repository
   - Check build logs for specific errors

3. **Docker Build Failed**
   - Verify service connection permissions
   - Check registry quota/space
   - Ensure repository name is correct

4. **Push to Registry Failed**
   - Verify service connection permissions
   - Check registry quota/space
   - Ensure repository name is correct

5. **Tests Failed**
   - Check application startup logs
   - Verify port mappings
   - Ensure dependencies are available

### Debug Tips

1. **Enable verbose logging**:
   ```yaml
   - script: |
       set -x  # Enable debug mode
       # your commands here
   ```

2. **Add diagnostic steps**:
   ```yaml
   - script: |
       docker images
       docker ps -a
       curl -v http://localhost:5000/
   ```

3. **Check container logs**:
   ```yaml
   - script: |
       docker logs price-tracker-test
   ```

## Pipeline Outputs

### Successful Run Produces:
- Docker image tagged with build ID
- Docker image tagged as `latest`
- Images pushed to `dock.ptslondon.co.uk/price-tracker:BUILD_ID`
- Deployment artifacts
- Test results

### Image Tags
- `dock.ptslondon.co.uk/price-tracker:latest` - Latest build
- `dock.ptslondon.co.uk/price-tracker:12345` - Specific build ID

## Production Deployment

For production deployment, the pipeline:
1. Only runs on `main` branch
2. Requires environment approval (if configured)
3. Runs security scans
4. Performs health checks
5. Can include notifications

## Monitoring

Monitor your pipeline:
1. **Pipeline runs**: Azure DevOps → Pipelines → Runs
2. **Environment status**: Azure DevOps → Pipelines → Environments
3. **Registry images**: Check your registry dashboard
4. **Application logs**: From deployed containers

## Next Steps

1. Set up monitoring and alerting for your deployed application
2. Configure backup strategies for your registry
3. Set up staging environments for testing
4. Add integration tests to the pipeline
5. Configure notification webhooks for deployment status

## Security Best Practices

1. **Never commit secrets** - Use Azure DevOps secure variables
2. **Use service connections** - Don't embed credentials
3. **Scan images** - Enable vulnerability scanning
4. **Limit permissions** - Use least privilege access
5. **Monitor access** - Regular audit of service connections
