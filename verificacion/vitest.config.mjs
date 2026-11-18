import {defineConfig} from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],test:{environment:'jsdom',include:['tests-ui/**/*.test.jsx'],pool:'threads',poolOptions:{threads:{singleThread:true}},testTimeout:10000}});
