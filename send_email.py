import smtplib
import sys
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, date
import argparse
import logging

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger("email_logger")

def clean_email_list(email_list):
    return [email.strip() for email in email_list if email.strip()]

def generate_email_body(workflow_result, build_id, repository, branch, commit, test_summary=None):
    
    today = date.today()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if workflow_result.lower() == 'success':
        status_text = "SUCCESS"
        status_color = "#28a745"
        header_bg = "#d4edda"
    else:
        status_text = "FAILED"
        status_color = "#dc3545"
        header_bg = "#f8d7da"
    
    # Build summary info
    summary_info = ""
    if test_summary:
        total_tests = test_summary.get('TotalTests', 0)
        passed_tests = test_summary.get('PassedTests', 0)
        failed_tests = test_summary.get('FailedTests', 0)
        
        summary_info = f"""
        <div style="margin: 20px 0;">
            <h3>Test Summary</h3>
            <ul>
                <li><strong>Total Tests:</strong> {total_tests}</li>
                <li><strong>Passed:</strong> <span style="color: #28a745;">{passed_tests}</span></li>
                <li><strong>Failed:</strong> <span style="color: #dc3545;">{failed_tests}</span></li>
            </ul>
        </div>
        """
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: {header_bg};
                padding: 20px;
                border-radius: 5px;
                text-align: center;
                margin-bottom: 20px;
                border: 1px solid {status_color};
            }}
            .status-badge {{
                display: inline-block;
                padding: 10px 20px;
                background-color: {status_color};
                color: white;
                border-radius: 3px;
                font-weight: bold;
                font-size: 18px;
            }}
            .info-section {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 3px;
                margin: 15px 0;
            }}
            .info-item {{
                margin: 8px 0;
            }}
            .info-item strong {{
                color: #555;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
                text-align: center;
            }}
            .report-link {{
                display: inline-block;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 3px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Nightly Build Report - HAMOA 1.1</h1>
            <div class="status-badge">{status_text}</div>
        </div>
        
        <div class="info-section">
            <h3>Build Information</h3>
            <div class="info-item"><strong>Date:</strong> {today}</div>
            <div class="info-item"><strong>Time:</strong> {timestamp}</div>
            <div class="info-item"><strong>Build ID:</strong> {build_id}</div>
            <div class="info-item"><strong>Repository:</strong> {repository}</div>
            <div class="info-item"><strong>Branch:</strong> {branch}</div>
            <div class="info-item"><strong>Commit:</strong> {commit[:8] if commit else 'N/A'}</div>
        </div>
        
        {summary_info}
        
        <div class="info-section">
            <h3>Next Steps</h3>
            <p>
                {'Build completed successfully.' if workflow_result.lower() == 'success' 
                 else 'Build failed.'}
            </p>
            <p>
                <strong>Detailed Report:</strong> Check the GitHub Actions workflow for the complete HTML report with detailed test results.
            </p>
        </div>
        
        <div class="footer">
            <p><strong>This is an automated email from the HAMOA 1.1 Nightly Build System</strong></p>
            <p>Generated at: {timestamp}</p>
        </div>
    </body>
    </html>
    """
    
    return html_body

def send_nightly_email(workflow_result, build_id, repository, branch, commit, 
                      recipient_emails, sender_email=None, 
                      test_summary=None, report_attachment=None):
    
    try:
        # Clean email lists
        recipients = clean_email_list(recipient_emails)
        
        if not recipients:
            logger.error("No recipient email addresses provided")
            return False
        
        # Sender email is required
        if not sender_email:
            logger.error("Sender email address is required")
            return False
        
        today = date.today()
        status_text = "SUCCESS" if workflow_result.lower() == 'success' else "FAILED"
        
        # Create email message
        msg = MIMEMultipart("alternative")
        msg['Subject'] = f"HAMOA 1.1 Nightly Build {status_text} - {today}"
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipients)
        
        # Generate and attach HTML body
        html_body = generate_email_body(workflow_result, build_id, repository, branch, commit, test_summary)
        msg.attach(MIMEText(html_body, 'html'))
        
        if report_attachment and os.path.exists(report_attachment):
            try:
                with open(report_attachment, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= nightly_build_report_{today}.html'
                )
                msg.attach(part)
                logging.info(f"Attached report file: {report_attachment}")
            except Exception as e:
                logging.warning(f"Could not attach report file: {e}")
        
        logging.info(f"Sending email to: {recipients}")
        
        # Connect to Qualcomm SMTP server (internal relay - no auth required)
        logging.info("Connecting to Qualcomm SMTP server...")
        smtp_server = smtplib.SMTP('smtphost.qualcomm.com')
        
        # For internal Qualcomm network, no authentication is typically required
        # The SMTP relay server handles authentication based on network location
        
        smtp_server.sendmail(sender_email, recipients, msg.as_string())
        smtp_server.quit()
        
        logging.info("Nightly build email sent successfully!")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send nightly build email: {e}")
        return False

def main():
    
    parser = argparse.ArgumentParser(description='Send nightly build status email')
    parser.add_argument('--workflow-result', required=True, choices=['success', 'failure'], 
                       help='Workflow result (success or failure)')
    parser.add_argument('--build-id', required=True, help='GitHub workflow run ID')
    parser.add_argument('--repository', required=True, help='Repository name')
    parser.add_argument('--branch', required=True, help='Branch name')
    parser.add_argument('--commit', required=True, help='Commit SHA')
    parser.add_argument('--recipients', required=True, help='Comma-separated list of recipient emails')
    parser.add_argument('--sender', help='Sender email address')
    parser.add_argument('--report-file', help='Path to HTML report file to attach')
    parser.add_argument('--total-tests', type=int, help='Total number of tests')
    parser.add_argument('--passed-tests', type=int, help='Number of passed tests')
    parser.add_argument('--failed-tests', type=int, help='Number of failed tests')
    
    args = parser.parse_args()
    
    # Parse email lists
    recipients = [email.strip() for email in args.recipients.split(',')]
    
    test_summary = None
    if args.total_tests is not None:
        test_summary = {
            'TotalTests': args.total_tests,
            'PassedTests': args.passed_tests or 0,
            'FailedTests': args.failed_tests or 0
        }
    
    # Send email
    success = send_nightly_email(
        workflow_result=args.workflow_result,
        build_id=args.build_id,
        repository=args.repository,
        branch=args.branch,
        commit=args.commit,
        recipient_emails=recipients,
        sender_email=args.sender,
        test_summary=test_summary,
        report_attachment=args.report_file
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
