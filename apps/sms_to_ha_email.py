import hassapi as hass
import requests
from huawei_lte_api.Connection import Connection
from huawei_lte_api.Client import Client
from huawei_lte_api.enums.sms import BoxTypeEnum

class SmsToHaEmail(hass.Hass):

    def initialize(self):
        """
        Initialize configuration parameters and schedule the recurring check.
        
        Reads the following from apps.yaml:
        - base_address: IP of the Huawei router.
        - username/password: Credentials for the router web UI.
        - notifier_name: Name of the HA notification service.
        - interval: How often to check for new messages (seconds).
        - batch_size: Number of messages to process in one page (default: 5).
        """
        self.base_address = self.args["base_address"]
        self.username = self.args["username"]
        self.password = self.args["password"]
        self.proxy_url = self.args.get("proxy_url")
        # Enforce lowercase to match Home Assistant service naming conventions
        self.notifier_name = self.args.get("notifier_name", "").lower()
        
        # Batch size for pagination (read_count)
        self.batch_size = int(self.args.get("batch_size", 5))

        # Templates for the notification content
        self.title_tpl = self.args.get("title_template", "New SMS: {sender}")
        self.body_tpl = self.args.get("body_template", "From: {sender}\nDate: {date}\n\n{content}")

        self.api_url = f"http://{self.username}:{self.password}@{self.base_address}/"
        interval = int(self.args.get("interval", 300))

        # Schedule the SMS check
        self.run_every(self.check_sms_box, "now", interval)
        self.log(f"Started monitoring {self.base_address} (batch size: {self.batch_size})")

    def check_sms_box(self, kwargs):
        """
        Iterate through the SMS inbox using pagination and process unread messages.
        
        Args:
            kwargs (dict): Arguments passed by the AppDaemon scheduler.
        """
        custom_session = requests.Session()
        if self.proxy_url:
            custom_session.proxies = {"http": self.proxy_url, "https": self.proxy_url}

        try:
            with Connection(self.api_url, requests_session=custom_session) as connection:
                client = Client(connection)
                page = 1
                total_forwarded = 0
                total_in_box = 0

                while True:
                    # Fetch a specific page of results using dynamic batch_size
                    sms_data = client.sms.get_sms_list(
                        page=page, 
                        read_count=self.batch_size, 
                        box_type=BoxTypeEnum.LOCAL_INBOX
                    )
                    messages = sms_data.get('Messages', {}).get('Message', [])

                    # Break loop if the current page is empty
                    if not messages:
                        break

                    if isinstance(messages, dict):
                        messages = [messages]
                    
                    total_in_box += len(messages)
                    
                    for msg in messages:
                        # Process only unread messages (Smstat == '0')
                        if msg.get('Smstat') == '0':
                            success = self.dispatch_notification(msg)
                            if success:
                                # Mark as read on the router after successful dispatch
                                client.sms.set_read(int(msg.get('Index')))
                                total_forwarded += 1

                    # Break if fewer messages were returned than the batch size (last page)
                    if len(messages) < self.batch_size:
                        break
                    else:
                        page += 1
                
                self.log(
                    f"Inbox processing finished. Total messages in inbox: {total_in_box}, "
                    f"Forwarded in this cycle: {total_forwarded}", 
                    level="DEBUG"
                )

        except Exception as e:
            self.log(f"Communication error with {self.base_address}: {e}", level="ERROR")
        finally:
            custom_session.close()

    def dispatch_notification(self, msg):
        """
        Format the message and forward it to the Home Assistant notification service.
        
        Args:
            msg (dict): Dictionary containing SMS data (Phone, Content, Date, Index, etc.).
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise.
        """
        try:
            sender = msg.get('Phone')
            content = msg.get('Content')
            date = msg.get('Date')

            # Prepare the email title and body based on templates
            mail_title = self.title_tpl.format(sender=sender, date=date, content=content)
            mail_body = self.body_tpl.format(sender=sender, date=date, content=content)

            # Call the HA notification service
            self.call_service(
                f"notify/{self.notifier_name}", 
                title=mail_title, 
                message=mail_body
            )

            self.log(f"SMS forwarded from {sender}")
            return True
        except Exception as e:
            self.log(f"Notification delivery error: {e}", level="ERROR")
            return False