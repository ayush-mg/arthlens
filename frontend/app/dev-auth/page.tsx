'use client';
import {useEffect} from 'react';
import {useRouter} from 'next/navigation';

export default function DevAuthPage(){
	const router=useRouter();
	useEffect(()=>{
		const token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNGQzYjRmYy0wYTI5LTQ3MjktOWEzZS0zYzRjNTNjZWQwZTQiLCJlbWFpbCI6ImF5dXNobWcyMDA3QGdtYWlsLmNvbSIsInJvbGVzIjpbIkVOVFJFUFJFTkVVUiJdLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwianRpIjoiZGI0OTY5MDktYWI3Ni00Y2NiLTljNTMtYmRiNTUwZTdiMjcxIiwiZXhwIjoxNzk1Mzk5ODEzLCJpYXQiOjE3OTQ3OTUwMTMuMzQwMjl9.K9XZetHmPwilWMk8cn-dQk9V1zwiw1u4ZZJTY9MZ9uk';
		localStorage.setItem('token',token);
		localStorage.setItem('arthlens_token',token);
		router.replace('/workspaces/22d1b23e-335d-4bd0-9355-176200229ce6/inventory');
	},[router]);

	return(
		<div className="p-10 font-mono text-sm text-[#231412] bg-[#FAF7F2] min-h-screen flex items-center justify-center">
			Authenticating workspace session...
		</div>
	);
}
