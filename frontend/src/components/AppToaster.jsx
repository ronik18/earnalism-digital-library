import { Toaster } from "sonner";

export function AppToaster(props) {
  return (
    <Toaster
      className="toaster"
      toastOptions={{
        classNames: {
          toast: "bg-beige-50 text-[#1C0A0E] border border-beige-300 shadow-book",
          description: "text-[#7A5C62]",
          actionButton: "bg-[#6B1020] text-beige-50",
          cancelButton: "bg-beige-200 text-[#7A5C62]",
        },
      }}
      {...props}
    />
  );
}
