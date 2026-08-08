import api from "../api/axios";

export const sendChatMessage = async (message, history = []) => {
    const response = await api.post("/ai/chat/", { message, history });
    return response.data;
};

const STATUS_MESSAGES = {
    401: "Your session has expired. Please sign in again.",
    403: "You do not have permission to use the AI assistant.",
    429: "The AI assistant is temporarily busy. Please try again in a moment.",
    500: "Something went wrong on the server. Please try again later.",
    502: "The AI service had trouble responding. Please try again later.",
    503: "The AI assistant is temporarily unavailable. Please try again soon.",
};

/**
 * Convert an Axios error (or a non-2xx backend response) into a friendly,
 * user-safe message.
 *
 * Order of preference:
 *  1. The backend's own friendly error (body.error.message), so server-side
 *     translations are honoured.
 *  2. Known HTTP status codes (rate limit, auth, server errors).
 *  3. Network-level failures (no response received).
 *  4. A generic fallback.
 */
export const getChatErrorMessage = (error) => {
    if (!error) return "Something went wrong. Please try again.";

    const data = error.response?.data;
    const backendError =
        data?.error?.message || data?.detail || data?.message;
    if (typeof backendError === "string" && backendError.trim()) {
        return backendError;
    }

    const status = error.response?.status;
    if (status && STATUS_MESSAGES[status]) return STATUS_MESSAGES[status];

    if (status >= 500) {
        return STATUS_MESSAGES[500];
    }

    if (!error.response) {
        return "Unable to reach the server. Check your connection and try again.";
    }

    return "Something went wrong. Please try again in a moment.";
};