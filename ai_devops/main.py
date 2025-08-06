"""
Main CLI entry point for AI DevOps Assistant Suite
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import click
import yaml
from dotenv import load_dotenv

from .monitor import WorkflowMonitor, PRMonitor
from .analyzer import CodeAnalyzer
from .exchanges import ExchangeManager
from .dashboard.server import DashboardServer
from .config.manager import ConfigManager

# Load environment variables
load_dotenv()

@click.group()
@click.version_option(version="1.0.0")
@click.option("--config", "-c", help="Path to configuration file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], verbose: bool):
    """
    AI DevOps Assistant Suite - Comprehensive DevOps automation with cryptocurrency exchange integration
    
    A powerful suite of tools for monitoring GitHub workflows, analyzing code with AI,
    integrating with cryptocurrency exchanges, and providing real-time insights.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    
    # Initialize configuration manager
    config_manager = ConfigManager(config_path=config)
    ctx.obj["config"] = config_manager


@cli.command()
@click.option("--repository", "-r", help="GitHub repository (owner/repo)")
@click.option("--exchanges", "-e", help="Comma-separated list of exchanges to analyze")
@click.option("--model", "-m", default="gpt-4", help="AI model to use for analysis")
@click.option("--output", "-o", help="Output file for analysis report")
@click.pass_context
def analyze(ctx: click.Context, repository: Optional[str], exchanges: Optional[str], model: str, output: Optional[str]):
    """Run comprehensive code analysis with exchange integration"""
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]
    
    if verbose:
        click.echo("Starting code analysis...")
    
    # Parse exchanges
    exchange_list = []
    if exchanges:
        exchange_list = [e.strip() for e in exchanges.split(",")]
    
    # Initialize analyzer
    analyzer = CodeAnalyzer(config=config.get_analyzer_config(), model=model)
    
    async def run_analysis():
        try:
            result = await analyzer.analyze_repository(
                repository=repository,
                exchanges=exchange_list,
                output_file=output
            )
            
            if verbose:
                click.echo(f"Analysis completed. Results: {result}")
            
            click.echo("✅ Code analysis completed successfully!")
            
        except Exception as e:
            click.echo(f"❌ Analysis failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(run_analysis())


@cli.command()
@click.option("--duration", "-d", default=3600, help="Monitoring duration in seconds")
@click.option("--interval", "-i", default=60, help="Check interval in seconds")
@click.option("--repository", "-r", help="GitHub repository to monitor")
@click.option("--exchanges", "-e", help="Comma-separated list of exchanges to monitor")
@click.pass_context
def monitor(ctx: click.Context, duration: int, interval: int, repository: Optional[str], exchanges: Optional[str]):
    """Start continuous monitoring of workflows and exchanges"""
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]
    
    if verbose:
        click.echo(f"Starting monitoring for {duration} seconds...")
    
    # Parse exchanges
    exchange_list = []
    if exchanges:
        exchange_list = [e.strip() for e in exchanges.split(",")]
    
    async def run_monitoring():
        try:
            # Initialize monitors
            workflow_monitor = WorkflowMonitor(config=config.get_monitor_config())
            pr_monitor = PRMonitor(config=config.get_monitor_config())
            
            if exchange_list:
                from .exchanges.monitor import ExchangeMonitor
                exchange_monitor = ExchangeMonitor(
                    config=config.get_exchange_config(),
                    exchanges=exchange_list
                )
                
                # Start exchange monitoring
                exchange_task = asyncio.create_task(
                    exchange_monitor.start_monitoring(interval=interval)
                )
            
            # Start workflow monitoring
            if repository:
                workflow_task = asyncio.create_task(
                    workflow_monitor.monitor_repository(repository, interval=interval)
                )
                pr_task = asyncio.create_task(
                    pr_monitor.monitor_repository(repository, interval=interval)
                )
            
            if verbose:
                click.echo("✅ Monitoring started successfully!")
            
            # Wait for duration
            await asyncio.sleep(duration)
            
            click.echo("⏱️ Monitoring duration completed.")
            
        except Exception as e:
            click.echo(f"❌ Monitoring failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(run_monitoring())


@cli.command()
@click.option("--host", default="localhost", help="Dashboard host")
@click.option("--port", default=8080, help="Dashboard port")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def dashboard(ctx: click.Context, host: str, port: int, debug: bool):
    """Launch the interactive web dashboard"""
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]
    
    if verbose:
        click.echo(f"Starting dashboard on {host}:{port}...")
    
    try:
        dashboard_server = DashboardServer(
            config=config,
            host=host,
            port=port,
            debug=debug
        )
        
        click.echo(f"🚀 Dashboard started at http://{host}:{port}")
        dashboard_server.run()
        
    except Exception as e:
        click.echo(f"❌ Dashboard failed to start: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--list", "list_exchanges", is_flag=True, help="List configured exchanges")
@click.option("--test", help="Test connection to specific exchange")
@click.option("--add", help="Add new exchange configuration")
@click.option("--remove", help="Remove exchange configuration")
@click.pass_context
def exchanges(ctx: click.Context, list_exchanges: bool, test: Optional[str], add: Optional[str], remove: Optional[str]):
    """Manage cryptocurrency exchange connections"""
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]
    
    exchange_manager = ExchangeManager(config=config.get_exchange_config())
    
    async def manage_exchanges():
        try:
            if list_exchanges:
                exchanges_list = await exchange_manager.list_exchanges()
                click.echo("📊 Configured exchanges:")
                for exchange in exchanges_list:
                    status = "✅" if exchange.get("connected") else "❌"
                    click.echo(f"  {status} {exchange['name']} - {exchange['status']}")
            
            elif test:
                result = await exchange_manager.test_connection(test)
                if result:
                    click.echo(f"✅ {test} connection successful!")
                else:
                    click.echo(f"❌ {test} connection failed!")
                    
            elif add:
                # Interactive exchange addition
                click.echo(f"Adding exchange: {add}")
                # Implementation for adding exchange
                
            elif remove:
                result = await exchange_manager.remove_exchange(remove)
                if result:
                    click.echo(f"✅ Removed {remove} successfully!")
                else:
                    click.echo(f"❌ Failed to remove {remove}!")
                    
            else:
                click.echo("Use --help to see available options")
                
        except Exception as e:
            click.echo(f"❌ Exchange management failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(manage_exchanges())


@cli.command()
@click.option("--period", default="daily", help="Report period (daily/weekly/monthly)")
@click.option("--output", "-o", help="Output file for report")
@click.option("--format", "output_format", default="json", help="Report format (json/html/pdf)")
@click.pass_context
def report(ctx: click.Context, period: str, output: Optional[str], output_format: str):
    """Generate periodic reports"""
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]
    
    if verbose:
        click.echo(f"Generating {period} report...")
    
    from .reports.generator import ReportGenerator
    
    async def generate_report():
        try:
            generator = ReportGenerator(config=config)
            
            report_data = await generator.generate_report(
                period=period,
                format=output_format,
                output_file=output
            )
            
            if output:
                click.echo(f"✅ Report saved to {output}")
            else:
                click.echo("📊 Report generated:")
                # Display summary
                
        except Exception as e:
            click.echo(f"❌ Report generation failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(generate_report())


@cli.command()
@click.pass_context
def setup(ctx: click.Context):
    """Interactive setup wizard for initial configuration"""
    config = ctx.obj["config"]
    
    click.echo("🚀 AI DevOps Assistant Setup Wizard")
    click.echo("=" * 50)
    
    # GitHub configuration
    click.echo("\n📍 GitHub Configuration")
    github_token = click.prompt("GitHub Personal Access Token", hide_input=True)
    
    # Exchange configuration
    click.echo("\n💰 Exchange Configuration")
    setup_exchanges = click.confirm("Would you like to configure cryptocurrency exchanges?")
    
    exchanges_config = {}
    if setup_exchanges:
        # International exchanges
        setup_binance = click.confirm("Configure Binance?")
        if setup_binance:
            exchanges_config["binance"] = {
                "api_key": click.prompt("Binance API Key", hide_input=True),
                "api_secret": click.prompt("Binance API Secret", hide_input=True),
                "sandbox": click.confirm("Use sandbox mode?", default=True)
            }
        
        # Iranian exchanges
        iranian_exchanges = click.confirm("Configure Iranian exchanges?")
        if iranian_exchanges:
            for exchange in ["wallex", "bitpin", "nobitex"]:
                if click.confirm(f"Configure {exchange.title()}?"):
                    exchanges_config[exchange] = {
                        "api_key": click.prompt(f"{exchange.title()} API Key", hide_input=True),
                        "api_secret": click.prompt(f"{exchange.title()} API Secret", hide_input=True),
                    }
    
    # AI configuration
    click.echo("\n🤖 AI Configuration")
    ai_provider = click.Choice(["openai", "anthropic"])
    ai_choice = click.prompt("AI Provider", type=ai_provider, default="openai")
    
    ai_config = {}
    if ai_choice == "openai":
        ai_config["openai"] = {
            "api_key": click.prompt("OpenAI API Key", hide_input=True),
            "model": click.prompt("Default model", default="gpt-4")
        }
    else:
        ai_config["anthropic"] = {
            "api_key": click.prompt("Anthropic API Key", hide_input=True),
            "model": click.prompt("Default model", default="claude-3-sonnet-20240229")
        }
    
    # Save configuration
    try:
        config.setup_initial_config(
            github_token=github_token,
            exchanges=exchanges_config,
            ai_config=ai_config
        )
        
        click.echo("\n✅ Configuration saved successfully!")
        click.echo("🎉 Setup completed! You can now use the AI DevOps Assistant.")
        click.echo("\nNext steps:")
        click.echo("  - Run 'ai-devops dashboard' to start the web interface")
        click.echo("  - Run 'ai-devops analyze --help' to see analysis options")
        click.echo("  - Run 'ai-devops monitor --help' to see monitoring options")
        
    except Exception as e:
        click.echo(f"❌ Setup failed: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()