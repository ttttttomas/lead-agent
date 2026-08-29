import "./globals.css";

export const metadata = {
  title: "Lead Agent",
  description: "AI-powered lead generation and qualification agent",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
