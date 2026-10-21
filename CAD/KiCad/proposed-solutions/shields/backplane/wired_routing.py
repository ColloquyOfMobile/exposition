"""Orthogonal routing; only straight, non-junction wire crossings are allowed."""
from collections import defaultdict
import heapq

DIRS=((1,0),(0,1),(-1,0),(0,-1))


class Router:
    def __init__(self,width,height,obstacles,pins):
        self.width,self.height=width,height
        self.obstacles,self.pins=obstacles,pins
        self.edges={}
        self.nodes=defaultdict(dict)
        self.trees=defaultdict(set)

    def add(self,net,a,b):
        edge=tuple(sorted((a,b)))
        assert edge not in self.edges or self.edges[edge]==net,(net,edge)
        self.edges[edge]=net
        for point,other in ((a,b),(b,a)):
            self.nodes[point].setdefault(net,set()).add((other[0]-point[0],other[1]-point[1]))
            self.trees[net].add(point)

    def line(self,net,a,b):
        assert a[0]==b[0] or a[1]==b[1]
        dx,dy=(b[0]>a[0])-(b[0]<a[0]),(b[1]>a[1])-(b[1]<a[1])
        while a!=b:
            nxt=a[0]+dx,a[1]+dy
            self.add(net,a,nxt)
            a=nxt

    def route(self,net,start,targets):
        if start in targets:return
        xs,ys=zip(*targets)
        lx,hx,ly,hy=min(xs),max(xs),min(ys),max(ys)
        def heuristic(q):return max(lx-q[0],0,q[0]-hx)+max(ly-q[1],0,q[1]-hy)
        initial=(start,-1)
        costs={initial:0}
        parent={}
        heap=[(heuristic(start),0,start,-1)]
        goal=None
        while heap:
            _,cost,point,previous=heapq.heappop(heap)
            state=point,previous
            if cost!=costs[state]:continue
            if point in targets:
                goal=state;break
            foreign_here=[ds for owner,ds in self.nodes.get(point,{}).items() if owner!=net]
            for direction,(dx,dy) in enumerate(DIRS):
                nxt=point[0]+dx,point[1]+dy
                if not(5<=nxt[0]<=self.width-5 and 19<=nxt[1]<=self.height-5):continue
                if nxt in self.obstacles:continue
                if nxt in self.pins and self.pins[nxt]!=net:continue
                if foreign_here and (previous<0 or direction!=previous):continue
                edge=tuple(sorted((point,nxt)))
                if edge in self.edges and self.edges[edge]!=net:continue
                foreign=[ds for owner,ds in self.nodes.get(nxt,{}).items() if owner!=net]
                if len(foreign)>1:continue
                if foreign:
                    perpendicular={(0,1),(0,-1)} if dx else {(1,0),(-1,0)}
                    if foreign[0]!=perpendicular:continue
                step=1+(8 if previous>=0 and direction!=previous else 0)+(2 if foreign else 0)
                step+=.12*sum(bool(self.nodes.get((nxt[0]+ox,nxt[1]+oy))) for ox,oy in DIRS)
                new_cost=cost+step
                key=nxt,direction
                if new_cost>=costs.get(key,float('inf')):continue
                costs[key]=new_cost;parent[key]=state
                heapq.heappush(heap,(new_cost+3*heuristic(nxt),new_cost,nxt,direction))
            if len(costs)>900000:raise RuntimeError('Routing search exhausted: '+net)
        if goal is None:raise RuntimeError(f'No route for {net} at {start}')
        points=[goal[0]]
        while goal!=initial:
            goal=parent[goal];points.append(goal[0])
        for a,b in zip(points,points[1:]):self.add(net,a,b)

    def segments(self,pin_nodes):
        while True:
            dead=[(p,net) for p,owners in self.nodes.items() if p not in pin_nodes
                  for net,ds in owners.items() if len(ds)==1]
            if not dead:break
            for point,net in dead:
                if net not in self.nodes.get(point,{}):continue
                directions=self.nodes[point][net]
                dx,dy=next(iter(directions));other=point[0]+dx,point[1]+dy
                self.edges.pop(tuple(sorted((point,other))))
                del self.nodes[point][net]
                if not self.nodes[point]:del self.nodes[point]
                self.nodes[other][net].discard((-dx,-dy))
                if not self.nodes[other][net]:del self.nodes[other][net]
        result=defaultdict(list);remaining=set(self.edges)
        while remaining:
            a,b=min(remaining);net=self.edges[a,b];remaining.remove((a,b))
            dx,dy=b[0]-a[0],b[1]-a[1]
            for reverse in (False,True):
                end=a if reverse else b
                sx,sy=(-dx,-dy) if reverse else (dx,dy)
                while len(self.nodes[end].get(net,()))==2 and end not in pin_nodes:
                    nxt=end[0]+sx,end[1]+sy;edge=tuple(sorted((end,nxt)))
                    if edge not in remaining or self.edges.get(edge)!=net:break
                    remaining.remove(edge);end=nxt
                if reverse:a=end
                else:b=end
            result[net].append((a,b))
        junctions=[p for p,owners in self.nodes.items() if any(len(ds)>=3 for ds in owners.values())]
        return result,junctions
