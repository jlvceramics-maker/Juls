import {Composition} from 'remotion';
import {Title} from './Title';

export const RemotionRoot: React.FC = () => (
	<Composition
		id="Title"
		component={Title}
		durationInFrames={90}
		fps={30}
		width={1080}
		height={1920}
		defaultProps={{text: 'Ретроград'}}
	/>
);
