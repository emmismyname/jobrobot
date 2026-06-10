from src import notifier


def test_company_discovery_email_only_sends_above_threshold(monkeypatch):
    sent_bodies = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, *_args):
            pass

        def send_message(self, message):
            sent_bodies.append(message.get_content())

    monkeypatch.setattr(notifier, "MIN_COMPANY_EMAIL_SCORE", 50)
    monkeypatch.setattr(notifier, "MAX_COMPANY_EMAILS", 25)
    monkeypatch.setattr(notifier, "get_env_value", lambda name: "x@example.com" if name != "EMAIL_APP_PASSWORD" else "secret")
    monkeypatch.setattr(notifier.smtplib, "SMTP_SSL", FakeSMTP)

    result = notifier.send_company_discovery_alert(
        [
            {
                "Company Name": "Low Co",
                "overall_company_score": 20,
                "Recommended Action": "Low Priority",
            },
            {
                "Company Name": "High Semi",
                "overall_company_score": 80,
                "Recommended Action": "Apply_Now",
            },
        ]
    )

    assert result is True
    assert "High Semi" in sent_bodies[0]
    assert "Low Co" not in sent_bodies[0]
