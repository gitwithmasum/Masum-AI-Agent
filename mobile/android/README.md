# Masum AI Agent Mobile v5.8

Native Android Cirilla / Geralt companion with smart app automation via safe Android intents and deep links.

## Smart app commands

```text
Hey Cirilla, YouTube search Python functions
Hey Cirilla, Chrome search machine learning roadmap
Hey Cirilla, Maps search BUBT
Hey Cirilla, navigate to BUBT
Hey Cirilla, search Masum AI Agent on GitHub
Hey Cirilla, search Notion on Play Store
Hey Cirilla, open WhatsApp chat with Rahim
```

Bangla examples:

```text
হেই সিরিলা, ইউটিউবে Python functions সার্চ করো
হেই সিরিলা, ক্রোমে machine learning roadmap সার্চ করো
হেই সিরিলা, ম্যাপে BUBT খুঁজে দাও
হেই সিরিলা, BUBT-তে নেভিগেট করো
হেই সিরিলা, গিটহাবে Masum AI Agent সার্চ করো
হেই সিরিলা, প্লে স্টোরে Notion সার্চ করো
হেই সিরিলা, রহিমের হোয়াটসঅ্যাপ চ্যাট খোলো
```

## How it works

- YouTube search opens a YouTube results deep link.
- Chrome/web search opens a Google search query.
- Maps search uses Android geo intents with a web fallback.
- Navigation uses Google Maps navigation intents.
- GitHub search opens GitHub search results.
- Play Store search uses the market intent with a web fallback.
- WhatsApp chat resolves the spoken contact from Android Contacts and opens the matching WhatsApp conversation without sending a message.

This phase prefers deterministic app intents instead of blind Accessibility clicking. Sensitive/password/security flows remain outside the automation allowlist.

All earlier v5.x features remain available.
