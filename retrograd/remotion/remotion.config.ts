import {Config} from '@remotion/cli/config';
import {existsSync, readdirSync} from 'fs';

// В облачной сессии нет доступа к remotion.media, поэтому берём предустановленный headless_shell от Playwright.
const pwBrowsers = '/opt/pw-browsers';
if (existsSync(pwBrowsers)) {
	const headlessShell = readdirSync(pwBrowsers)
		.filter((dir) => dir.startsWith('chromium_headless_shell-'))
		.map((dir) => `${pwBrowsers}/${dir}/chrome-linux/headless_shell`)
		.find((path) => existsSync(path));
	if (headlessShell) {
		Config.setBrowserExecutable(headlessShell);
	}
}
