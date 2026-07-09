import type { ReactNode } from "react";

export const metadata = {
  title: "Authentication | EchoTrace AI",
};

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-md animate-in">{children}</div>
      </div>
    </div>
  );
}
