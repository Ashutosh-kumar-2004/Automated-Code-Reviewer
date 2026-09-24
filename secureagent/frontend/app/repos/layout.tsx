import AppLayout from "@/components/layout/AppLayout";

export default function ReposLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppLayout>{children}</AppLayout>;
}
