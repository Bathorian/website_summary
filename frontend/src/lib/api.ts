export const Local = 'http://localhost:8000'

export function Environment(env: 'prod' | 'test'): string {
    if (env === 'prod') {
        return 'https://website-summary-backend.fly.dev' // replace with actual prod URL
    }
    return 'https://website-summary-backend-test.fly.dev' // replace with actual test URL
}

export function PreviewEnv(prID: string | number): string {
    return `https://website-summary-backend-pr-${prID}.fly.dev`
}
