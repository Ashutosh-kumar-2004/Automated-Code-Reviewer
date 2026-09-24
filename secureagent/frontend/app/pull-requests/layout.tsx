import AppLayout from "@/components/layout/AppLayout";

export default function PullRequestsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppLayout>{children}</AppLayout>;
}
