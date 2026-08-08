# Google Play data safety draft

[English](play-data-safety-en.md) | [Türkçe](play-data-safety.md)

- No data is collected by or shared with a developer-operated server.
- User-entered URLs are used only in requests to the media source.
- Queue data, history, settings, and logs remain on the device.
- The application has no account creation or in-app Google sign-in.
- The application does not use advertising, location, contacts, photo scanning,
  or financial data.
- Network, notification, and user-initiated long-download permissions are used
  for core functionality.

Before submitting the Play Console form, audit any SDKs added later and verify
the application's actual network traffic again.
