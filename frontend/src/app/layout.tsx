import '../styles/globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'FinancialWatch: Misinformation & Reputational Risk Intelligence',
  description: 'AI-driven intelligence pipeline for monitoring, classifying, and countering false narratives targeting Nigerian financial institutions.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>{children}</body>
    </html>
  );
}
