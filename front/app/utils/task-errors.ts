/**
 * Persian text for the task API's (English) error messages, so the task pages stay
 * fully Persian even when the server refuses something. Unknown messages fall back to
 * the caller's own Persian text.
 */
const RULES: [RegExp, string][] = [
  [/only a manager can/i, 'این کار فقط توسط مدیر قابل انجام است.'],
  [/belongs to another department/i, 'این امور محوله متعلق به واحد یا دپارتمان دیگری است.'],
  [/only create tasks in your own department/i, 'فقط می‌توانید در واحد خودتان امور محوله ایجاد کنید.'],
  [/only a current assignee can refer/i, 'فقط مسئول فعلی امور محوله می‌تواند آن را ارجاع دهد.'],
  [/refer a task to yourself/i, 'نمی‌توانید امور محوله را به خودتان ارجاع دهید.'],
  [/cannot be referred/i, 'امور محوله‌ی انجام‌شده یا لغوشده قابل ارجاع نیست.'],
  [/already assigned/i, 'این فرد از قبل مسئول این امور محوله است.'],
  [/not a member of this task's team|does not belong to this task's department|not active/i, 'مسئول باید عضو فعال تیم یا واحد این امور محوله باشد.'],
  [/cannot be mentioned/i, 'این کاربر به امور محوله دسترسی ندارد و نمی‌توان او را منشن کرد.'],
  [/only the task's people can attach files/i, 'فقط افراد مرتبط با امور محوله می‌توانند فایل پیوست کنند.'],
  [/file type is not allowed/i, 'نوع این فایل مجاز نیست.'],
  [/too large/i, 'حجم فایل بیش از حد مجاز است.'],
  [/file is empty/i, 'فایل خالی است.'],
  [/no file was sent/i, 'هیچ فایلی انتخاب نشده است.'],
  [/as the assignee you can only change the status/i, 'به‌عنوان مسئول فقط می‌توانید «درخواست تأیید تکمیل» را ثبت کنید.'],
  [/missing permission|permission_denied/i, 'شما دسترسی لازم برای این کار را ندارید.'],
  [/was not found/i, 'مورد درخواستی پیدا نشد.'],
]

export function taskErrorMessage(err: unknown, fallback: string): string {
  const text = err instanceof Error ? err.message : typeof err === 'string' ? err : ''
  if (!text) return fallback
  if (/[\u0600-\u06FF]/.test(text)) return text // already Persian
  for (const [re, fa] of RULES) if (re.test(text)) return fa
  return fallback
}
