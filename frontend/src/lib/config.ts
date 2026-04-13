import {Environment, Local, PreviewEnv} from '@/lib/api.ts'

const isProduction = import.meta.env.VITE_VERCEL_ENV === 'production'
const isPreview = import.meta.env.VITE_VERCEL_ENV === 'preview'
const isTest = import.meta.env.VITE_VERCEL_GIT_COMMIT_REF === 'test'
const prID = import.meta.env.VITE_VERCEL_GIT_PULL_REQUEST_ID

export const AppConfig = {
    // apiUrl is the base url of the backend API
    apiUrl: getAPIBaseURL(),

    // label text for the current environment (if not production)
    envLabel: getEnvLabel(),

    // label color for the current environment (if not production)
    envColor: getEnvColor(),
}

// backend API url
function getAPIBaseURL() {
    if (isProduction) {
        return Environment('prod') // prod deployment url
    }
    if (isTest) {
        return Environment('test') // test deployment url
    }
    if (isPreview) {
        return PreviewEnv(prID) // pr deployment url
    }
    return Local // localhost backend
}

function getEnvLabel(): string | null {
    if (isProduction) return null
    if (isTest) return 'TESTING'
    if (isPreview) return `PREVIEW (PR #${prID})`
    return 'LOCAL'
}

function getEnvColor(): string {
    if (isPreview) return 'bg-orange-500'
    if (isTest) return 'bg-yellow-500'
    return 'bg-blue-500'
}
