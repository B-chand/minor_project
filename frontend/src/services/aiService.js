import api from "../api/axios";

const STATUS_MESSAGES = {
    401: "Your session has expired. Please sign in again.",
    403: "You do not have permission to access this data.",
    404: "The requested AI data could not be found.",
    429: "The AI service is temporarily busy. Please try again in a moment.",
    500: "Something went wrong on the server while running the AI analysis.",
    502: "The AI service had trouble responding. Please try again later.",
    503: "The AI service is temporarily unavailable. Please try again soon.",
};

/**
 * Convert an Axios error (or a non-2xx backend response) into a friendly,
 * user-safe message for the AI endpoints.
 *
 * Order of preference:
 *  1. The backend's own error body (error.message, then detail, then message).
 *  2. Known HTTP status codes (auth, permission, rate limit, server errors).
 *  3. Network-level failures (no response received).
 *  4. A generic fallback.
 */
export const getErrorMessage = (error) => {
    if (!error) return "Something went wrong while loading AI data.";

    const data = error.response?.data;
    const backendError = data?.error?.message || data?.detail || data?.message;
    if (typeof backendError === "string" && backendError.trim()) {
        return backendError;
    }

    const status = error.response?.status;

    if (status === 404 && typeof data === "string") {
        return "The AI data endpoint is not available on this server. Please make sure the backend is up to date and the AI module is enabled.";
    }

    if (status && STATUS_MESSAGES[status]) {
        return STATUS_MESSAGES[status];
    }

    // axios aborts with ECONNABORTED when the request exceeds the client
    // timeout. The backend may still be running (AI analysis is slow, e.g.
    // the demand-forecast model under load) — do not claim it is unreachable.
    if (error.code === "ECONNABORTED") {
        return "The AI analysis is taking longer than expected. Please try again in a moment.";
    }

    if (!error.response) {
        return "Unable to reach the server. Check your connection and try again.";
    }

    return "Something went wrong while loading AI data. Please try again.";
};

export const getForecastDetail = async () => {
    const response = await api.get("/ai/forecast-detail/");
    return response.data;
};

export const getRecommendations = async () => {
    const response = await api.get("/ai/recommendation/");
    return response.data;
};

export const getAIDashboard = async () => {
    const response = await api.get("/ai/dashboard/");
    return response.data;
};

export const getBusinessIntelligence = async (params = {}) => {
    const response = await api.get("/ai/business-intelligence/", { params });
    return response.data;
};

export const getInventorySummary = async () => {
    const response = await api.get("/ai/inventory-summary/");
    return response.data;
};