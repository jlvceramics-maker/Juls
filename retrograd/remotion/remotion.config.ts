import {Config} from '@remotion/cli/config';
import {existsSync} from 'fs';

// В облачной сессии нет доступа к remotion.media, поэтому берём предустановленный headless_shell.
const headlessShell = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
if (existsSync(headlessShell)) {
	Config.setBrowserExecutable(headlessShell);
}
