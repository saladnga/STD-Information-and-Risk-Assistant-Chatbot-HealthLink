import { App } from "antd";

// Centralizes toasts + confirm dialogs (antd) so components call notify.success(...) / notify.confirm(...) instead of wiring antd directly.
export function useNotify() {
  const { message, modal } = App.useApp();

  return {
    success: (content: string) => message.success(content),
    error: (content: string) => message.error(content),
    confirm: (options: {
      title: string;
      content?: string;
      okText?: string;
      danger?: boolean;
      onOk: () => void;
    }) =>
      modal.confirm({
        title: options.title,
        content: options.content,
        okText: options.okText ?? "Yes",
        cancelText: "Cancel",
        okButtonProps: { danger: options.danger },
        onOk: options.onOk,
      }),
  };
}
