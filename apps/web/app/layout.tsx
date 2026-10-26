import "./globals.css";

export const metadata = {
  title: process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "example",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
