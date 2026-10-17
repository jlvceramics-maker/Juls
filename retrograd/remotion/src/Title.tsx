import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

export const Title: React.FC<{text: string}> = ({text}) => {
	const frame = useCurrentFrame();
	const opacity = interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{backgroundColor: '#111', justifyContent: 'center', alignItems: 'center'}}>
			<div style={{color: 'white', fontSize: 120, fontFamily: 'serif', opacity}}>{text}</div>
		</AbsoluteFill>
	);
};
