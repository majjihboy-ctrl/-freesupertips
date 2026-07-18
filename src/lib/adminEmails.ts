// Always an admin regardless of whether VITE_ADMIN_EMAILS is configured
// correctly in the current environment — this account should never get
// accidentally locked out by a missing/misconfigured env var.
const PERMANENT_ADMIN_EMAILS = ['majjihboy@gmail.com'];

export function isAdminEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const envAdminEmails = (import.meta.env.VITE_ADMIN_EMAILS || '')
    .split(',')
    .map((e: string) => e.trim().toLowerCase())
    .filter(Boolean);
  const adminEmails = [...new Set([...PERMANENT_ADMIN_EMAILS, ...envAdminEmails])];
  return adminEmails.includes(email.toLowerCase());
}
